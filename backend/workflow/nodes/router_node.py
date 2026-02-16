from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class RouterNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = str(context.get("user_input", ""))
        context["intent"] = "code" if "code" in user_input.lower() else "chat"
        return context
