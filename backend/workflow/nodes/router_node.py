from __future__ import annotations

from typing import Any

from .base_node import BaseNode


_RESEARCH_MARKERS = (
    "research",
    "search",
    "find",
    "look up",
    "sources",
    "citations",
)

_PLANNING_MARKERS = (
    "plan",
    "planning",
    "break down",
    "breakdown",
    "steps",
    "step by step",
    "tasks",
    "task list",
    "schedule",
    "outline",
    "agenda",
)

_WRITING_MARKERS = (
    "write",
    "writing",
    "draft",
    "compose",
    "letter",
    "email",
    "report",
    "essay",
    "document",
    "summarize",
    "summary",
)


class RouterNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = str(context.get("user_input", "")).lower()
        if "code" in user_input:
            intent = "code"
        elif any(marker in user_input for marker in _RESEARCH_MARKERS):
            intent = "research"
        elif any(marker in user_input for marker in _PLANNING_MARKERS):
            intent = "planning"
        elif any(marker in user_input for marker in _WRITING_MARKERS):
            intent = "writing"
        else:
            intent = "chat"

        context["intent"] = intent
        return context
