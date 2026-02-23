from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.file_tools import build_file_tool_dispatch_map, register_core_file_tools
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
        sandbox_roots_raw = tool_call.get("sandbox_roots")

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

        request = ToolExecutionRequest(
            tool_name=tool_name,
            payload=payload,
            allow_write_safe=allow_write_safe,
        )
        ok, result = execute_tool_call(
            request=request,
            registry=registry,
            sandbox=sandbox,
            dispatch_map=build_file_tool_dispatch_map(),
        )

        context["tool_ok"] = ok
        context["tool_result"] = result
        context["tool_name"] = tool_name
        context["tool_call_status"] = "executed" if ok else "failed"
        return context
