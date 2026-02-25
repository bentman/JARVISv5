from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from backend.cache.key_policy import make_cache_key
from backend.cache.metrics import get_metrics
from backend.cache.redis_client import RedisCacheClient
from backend.cache.settings import load_cache_settings
from backend.security.privacy_wrapper import ExternalCallRequest, PrivacyExternalCallWrapper
from backend.tools.registry import PermissionTier, ToolRegistry
from backend.tools.sandbox import Sandbox


ToolDispatchHandler = Callable[[Sandbox, dict[str, Any]], tuple[bool, dict[str, Any]]]


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    allow_write_safe: bool = False
    external_call: bool = False
    allow_external: bool = False
    external_provider: str | None = None
    external_endpoint: str | None = None
    redaction_mode: Literal["partial", "strict"] = "strict"
    task_id: str | None = None


def execute_tool_call(
    request: ToolExecutionRequest,
    registry: ToolRegistry,
    sandbox: Sandbox,
    dispatch_map: dict[str, ToolDispatchHandler],
    privacy_wrapper: PrivacyExternalCallWrapper | None = None,
    cache_client: RedisCacheClient | None = None,
    enable_caching: bool = True,
) -> tuple[bool, dict[str, Any]]:
    tool = registry.get(request.tool_name)
    if tool is None:
        return False, {
            "code": "tool_not_found",
            "tool_name": request.tool_name,
            "message": f"Tool not found: {request.tool_name}",
            "errors": [],
        }

    validated_ok, validated_payload_or_error = registry.validate_input(request.tool_name, request.payload)
    if not validated_ok:
        return False, validated_payload_or_error

    if privacy_wrapper is not None and not request.external_call:
        privacy_wrapper.scan_tool_input(
            tool_name=request.tool_name,
            payload=validated_payload_or_error,
            redaction_mode=request.redaction_mode,
            task_id=request.task_id,
        )

    if request.external_call:
        if privacy_wrapper is None:
            return False, {
                "code": "configuration_error",
                "tool_name": request.tool_name,
                "message": "privacy_wrapper is required for external_call",
            }
        privacy_ok, privacy_result = privacy_wrapper.evaluate_and_prepare_external_call(
            ExternalCallRequest(
                provider=request.external_provider or request.tool_name,
                endpoint=request.external_endpoint or request.tool_name,
                payload=validated_payload_or_error,
                task_id=request.task_id,
                allow_external=request.allow_external,
                redaction_mode=request.redaction_mode,
            )
        )
        if not privacy_ok:
            return False, privacy_result

    if tool.permission_tier == PermissionTier.WRITE_SAFE and not request.allow_write_safe:
        return False, {
            "code": "permission_denied",
            "tool_name": request.tool_name,
            "message": "write_safe permission required",
            "required_permission": PermissionTier.WRITE_SAFE.value,
        }

    if tool.permission_tier == PermissionTier.SYSTEM:
        return False, {
            "code": "permission_denied",
            "tool_name": request.tool_name,
            "message": "system permission is not enabled",
            "required_permission": PermissionTier.SYSTEM.value,
        }

    cache_metrics = get_metrics()
    cacheable = (
        cache_client is not None
        and enable_caching
        and load_cache_settings().cache_enabled
        and tool.permission_tier == PermissionTier.READ_ONLY
        and privacy_wrapper is None
    )
    active_cache_client = cache_client if cacheable else None
    cache_key: str | None = None

    if active_cache_client is not None:
        try:
            cache_key = make_cache_key(
                "tool",
                parts={"tool_name": request.tool_name, "payload": request.payload},
            )
            cached_result = active_cache_client.get_json(cache_key)
            if isinstance(cached_result, dict):
                cache_metrics.record_hit("tool")
                returned = dict(cached_result)
                returned["cache_hit"] = True
                return True, returned
            cache_metrics.record_miss("tool")
        except Exception:
            cache_metrics.record_miss("tool")

    handler = dispatch_map.get(request.tool_name)
    if handler is None:
        return False, {
            "code": "tool_not_implemented",
            "tool_name": request.tool_name,
            "message": f"Tool handler not implemented: {request.tool_name}",
        }

    try:
        ok, result = handler(sandbox, validated_payload_or_error)
    except Exception as exc:
        return False, {
            "code": "execution_error",
            "tool_name": request.tool_name,
            "message": f"Tool execution failed: {exc}",
        }

    if not isinstance(result, dict):
        return False, {
            "code": "execution_error",
            "tool_name": request.tool_name,
            "message": "Tool execution returned invalid result shape",
        }

    if privacy_wrapper is not None:
        output_scan = privacy_wrapper.scan_tool_output(
            tool_name=request.tool_name,
            result=result,
            redaction_mode=request.redaction_mode,
            task_id=request.task_id,
        )
        result = dict(result)
        result["privacy"] = {
            "pii_detected": output_scan["pii_detected"],
            "pii_redacted": output_scan["pii_redacted"],
            "summary": output_scan["summary"],
            "mode": output_scan["mode"],
        }
        result["redacted_result_text"] = output_scan["result_text"]

    if active_cache_client is not None:
        result = dict(result)
        result["cache_hit"] = False
        if ok and cache_key is not None:
            try:
                ttl_seconds = load_cache_settings().tool_cache_ttl_seconds
                if active_cache_client.set_json(cache_key, dict(result), ttl=ttl_seconds):
                    cache_metrics.record_set()
            except Exception:
                pass

    return bool(ok), result
