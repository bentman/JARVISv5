from __future__ import annotations

from typing import Any

from .base_node import BaseNode


class ContextBuilderNode(BaseNode):
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        memory_manager = context.get("memory_manager")
        task_id = context.get("task_id")

        if memory_manager is None:
            context["working_state"] = None
            context["context_builder_error"] = "memory_manager_missing"
            return context

        if not task_id:
            context["working_state"] = None
            context["context_builder_error"] = "task_id_missing"
            return context

        context["working_state"] = memory_manager.get_task_state(str(task_id))
        return context
