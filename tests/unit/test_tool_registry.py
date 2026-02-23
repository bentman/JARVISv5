from pydantic import BaseModel, Field

from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry


class AlphaInput(BaseModel):
    path: str = Field(min_length=1)


class BetaInput(BaseModel):
    count: int = Field(ge=1)


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="beta_tool",
            description="Beta tool",
            permission_tier=PermissionTier.WRITE_SAFE,
            input_model=BetaInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="alpha_tool",
            description="Alpha tool",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=AlphaInput,
        )
    )
    return registry


def test_register_and_lookup_tool() -> None:
    registry = _make_registry()

    alpha = registry.get("alpha_tool")
    assert alpha is not None
    assert alpha.description == "Alpha tool"

    tool_names = [tool.name for tool in registry.list_tools()]
    assert tool_names == ["alpha_tool", "beta_tool"]


def test_register_duplicate_name_rejected() -> None:
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="dup_tool",
        description="Duplicate test",
        permission_tier=PermissionTier.READ_ONLY,
        input_model=AlphaInput,
    )
    registry.register(tool)

    try:
        registry.register(tool)
        raise AssertionError("Expected ValueError for duplicate tool name")
    except ValueError as exc:
        assert "Tool already registered: dup_tool" in str(exc)


def test_validate_input_success() -> None:
    registry = _make_registry()

    ok, payload = registry.validate_input("alpha_tool", {"path": "README.md"})
    assert ok is True
    assert payload == {"path": "README.md"}


def test_validate_input_failure_returns_structured_error() -> None:
    registry = _make_registry()

    ok, error = registry.validate_input("beta_tool", {"count": 0})
    assert ok is False
    assert error["code"] == "validation_error"
    assert error["tool_name"] == "beta_tool"
    assert error["message"] == "Input validation failed"
    assert isinstance(error["errors"], list)
    assert error["errors"][0]["loc"] == ("count",)


def test_validate_input_unknown_tool_fail_closed() -> None:
    registry = _make_registry()

    ok, error = registry.validate_input("missing_tool", {"path": "x"})
    assert ok is False
    assert error == {
        "code": "tool_not_found",
        "tool_name": "missing_tool",
        "message": "Tool not found: missing_tool",
        "errors": [],
    }


def test_export_schema_shape_and_stable_ordering() -> None:
    registry = _make_registry()

    alpha_schema = registry.export_tool_schema("alpha_tool")
    assert alpha_schema["name"] == "alpha_tool"
    assert alpha_schema["description"] == "Alpha tool"
    assert alpha_schema["permission_tier"] == "read_only"
    assert "input_schema" in alpha_schema
    assert alpha_schema["input_schema"]["type"] == "object"

    all_schemas_first = registry.export_all_schemas()
    all_schemas_second = registry.export_all_schemas()

    assert [item["name"] for item in all_schemas_first] == ["alpha_tool", "beta_tool"]
    assert all_schemas_first == all_schemas_second
