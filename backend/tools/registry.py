from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError


class PermissionTier(str, Enum):
    READ_ONLY = "read_only"
    WRITE_SAFE = "write_safe"
    SYSTEM = "system"


class ToolDefinition(BaseModel):
    name: str
    description: str
    permission_tier: PermissionTier
    input_model: type[BaseModel]


class ToolValidationException(Exception):
    """Raised for registry validation failures."""


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return [self._tools[name] for name in sorted(self._tools.keys())]

    def validate_input(self, tool_name: str, payload: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        tool = self.get(tool_name)
        if tool is None:
            return False, {
                "code": "tool_not_found",
                "tool_name": tool_name,
                "message": f"Tool not found: {tool_name}",
                "errors": [],
            }

        try:
            validated = tool.input_model.model_validate(payload)
            return True, validated.model_dump()
        except ValidationError as exc:
            return False, {
                "code": "validation_error",
                "tool_name": tool_name,
                "message": "Input validation failed",
                "errors": exc.errors(),
            }

    def export_tool_schema(self, tool_name: str) -> dict[str, Any]:
        tool = self.get(tool_name)
        if tool is None:
            raise ToolValidationException(f"Tool not found: {tool_name}")

        return {
            "name": tool.name,
            "description": tool.description,
            "permission_tier": tool.permission_tier.value,
            "input_schema": tool.input_model.model_json_schema(),
        }

    def export_all_schemas(self) -> list[dict[str, Any]]:
        return [self.export_tool_schema(name) for name in sorted(self._tools.keys())]
