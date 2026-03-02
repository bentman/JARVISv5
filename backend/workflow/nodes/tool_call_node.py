from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Literal, cast

import backend.security.audit_logger as audit_logger_module
from backend.security.audit_logger import SecurityAuditLogger
from backend.security.privacy_wrapper import PrivacyExternalCallWrapper
from backend.security.redactor import PIIRedactor
from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.file_tools import build_file_tool_dispatch_map, register_core_file_tools
from backend.tools.search_tools import build_search_tool_dispatch_map, register_search_tools
from backend.tools.registry import ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig
from backend.workflow.nodes.base_node import BaseNode


class ToolCallNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        tool_call = context.get("tool_call")
        if not isinstance(tool_call, dict):
            context["tool_ok"] = False
            context["tool_result"] = {
                "code": "tool_call_missing",
                "message": "tool_call payload is missing",
            }
            context["tool_call_status"] = "failed"
            return context

        tool_name = str(tool_call.get("tool_name", "")).strip()
        payload = tool_call.get("payload", {})
        allow_write_safe = bool(tool_call.get("allow_write_safe", False))
        external_call = bool(tool_call.get("external_call", False))
        allow_external = bool(tool_call.get("allow_external", False))
        external_provider_raw = tool_call.get("external_provider")
        external_endpoint_raw = tool_call.get("external_endpoint")
        redaction_mode_raw = str(tool_call.get("redaction_mode", "strict")).strip().lower()
        redaction_mode: Literal["partial", "strict"] = (
            cast(Literal["partial", "strict"], redaction_mode_raw)
            if redaction_mode_raw in {"partial", "strict"}
            else "strict"
        )
        task_id = str(tool_call.get("task_id") or context.get("task_id") or "")
        audit_log_path_raw = tool_call.get("audit_log_path")
        sandbox_roots_raw = tool_call.get("sandbox_roots")
        search_payload_loader_raw = tool_call.get("search_payload_loader")
        fetch_html_loader_raw = tool_call.get("fetch_html_loader")

        if not tool_name:
            context["tool_ok"] = False
            context["tool_result"] = {
                "code": "tool_name_missing",
                "message": "tool_name is required",
            }
            context["tool_call_status"] = "failed"
            return context

        if not isinstance(payload, dict):
            context["tool_ok"] = False
            context["tool_result"] = {
                "code": "invalid_payload",
                "message": "payload must be an object",
            }
            context["tool_call_status"] = "failed"
            return context

        if not isinstance(sandbox_roots_raw, (list, tuple)) or not sandbox_roots_raw:
            context["tool_ok"] = False
            context["tool_result"] = {
                "code": "sandbox_roots_missing",
                "message": "sandbox_roots must be a non-empty list",
            }
            context["tool_call_status"] = "failed"
            return context

        sandbox_roots = tuple(Path(str(root)).resolve() for root in sandbox_roots_raw)
        sandbox = Sandbox(
            SandboxConfig(
                allowed_roots=sandbox_roots,
                allow_write=allow_write_safe,
                allow_delete=allow_write_safe,
            )
        )
        registry = ToolRegistry()
        register_core_file_tools(registry, sandbox)
        dispatch_map = build_file_tool_dispatch_map()

        if tool_name in {"search_web", "fetch_url"}:
            register_search_tools(registry)

            search_payload_loader = (
                cast(Callable[[str, str], dict | str], search_payload_loader_raw)
                if callable(search_payload_loader_raw)
                else None
            )
            fetch_html_loader = (
                cast(Callable[[str], str], fetch_html_loader_raw)
                if callable(fetch_html_loader_raw)
                else None
            )

            search_dispatch_map = build_search_tool_dispatch_map(
                allow_external=allow_external,
                task_id=task_id or None,
                date_key=str(tool_call.get("date_key")).strip() if tool_call.get("date_key") is not None else None,
                budget_ledger=SearchBudgetLedger(),
                budget_config=SearchBudgetConfig(),
                search_payload_loader=search_payload_loader,
                fetch_html_loader=fetch_html_loader,
            )
            dispatch_map = {**dispatch_map, **search_dispatch_map}

        request = ToolExecutionRequest(
            tool_name=tool_name,
            payload=payload,
            allow_write_safe=allow_write_safe,
            external_call=external_call,
            allow_external=allow_external,
            external_provider=str(external_provider_raw) if external_provider_raw is not None else None,
            external_endpoint=str(external_endpoint_raw) if external_endpoint_raw is not None else None,
            redaction_mode=redaction_mode,
            task_id=task_id or None,
        )
        audit_log_path = ""
        if audit_log_path_raw is not None:
            audit_log_path = str(audit_log_path_raw).strip()
        if audit_log_path:
            audit_logger = SecurityAuditLogger(audit_log_path)
        else:
            audit_logger = audit_logger_module.create_default_audit_logger()
        privacy_wrapper = PrivacyExternalCallWrapper(
            redactor=PIIRedactor(),
            audit_logger=audit_logger,
        )
        ok, result = execute_tool_call(
            request=request,
            registry=registry,
            sandbox=sandbox,
            dispatch_map=dispatch_map,
            privacy_wrapper=privacy_wrapper,
        )

        context["tool_ok"] = ok
        context["tool_result"] = result
        context["tool_name"] = tool_name
        context["tool_call_status"] = "executed" if ok else "failed"
        return context
