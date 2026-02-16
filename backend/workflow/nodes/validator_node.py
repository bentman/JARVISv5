from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class ValidatorNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        output = context.get("llm_output", "")
        context["is_valid"] = bool(str(output).strip())
        return context
