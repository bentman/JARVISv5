from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from backend.tools.registry import PermissionTier, ToolRegistry
from backend.tools.sandbox import Sandbox


ToolDispatchHandler = Callable[[Sandbox, dict[str, Any]], tuple[bool, dict[str, Any]]]


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    allow_write_safe: bool = False


def execute_tool_call(
    request: ToolExecutionRequest,
    registry: ToolRegistry,
    sandbox: Sandbox,
    dispatch_map: dict[str, ToolDispatchHandler],
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

    return bool(ok), result
