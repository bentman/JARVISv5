from pathlib import Path

from pydantic import BaseModel

from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig


class _ExternalInput(BaseModel):
    query: str


class _ReadOnlyInput(BaseModel):
    value: str


class _WriteSafeInput(BaseModel):
    path: str


def _make_registry_and_sandbox(root: Path) -> tuple[ToolRegistry, Sandbox]:
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,)))
    registry = ToolRegistry()
    return registry, sandbox


def test_external_denied_by_default(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _make_registry_and_sandbox(root)
    registry.register(
        ToolDefinition(
            name="external_tool",
            description="External tool",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=_ExternalInput,
        )
    )

    called = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        called["count"] += 1
        return True, {"code": "ok"}

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="external_tool",
            payload={"query": "test"},
            allow_external=False,
        ),
        registry,
        sandbox,
        {"external_tool": _handler},
    )

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["message"] == "external permission required"
    assert result["required_permission"] == PermissionTier.EXTERNAL.value
    assert called["count"] == 0


def test_external_allowed_with_flag(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _make_registry_and_sandbox(root)
    registry.register(
        ToolDefinition(
            name="external_tool",
            description="External tool",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=_ExternalInput,
        )
    )

    called = {"count": 0}

    def _handler(_sandbox: Sandbox, payload: dict) -> tuple[bool, dict]:
        called["count"] += 1
        return True, {"code": "ok", "echo": payload["query"]}

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="external_tool",
            payload={"query": "test"},
            allow_external=True,
        ),
        registry,
        sandbox,
        {"external_tool": _handler},
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["echo"] == "test"
    assert called["count"] == 1


def test_read_only_unchanged_without_allow_external(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _make_registry_and_sandbox(root)
    registry.register(
        ToolDefinition(
            name="read_only_tool",
            description="Read-only tool",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=_ReadOnlyInput,
        )
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="read_only_tool",
            payload={"value": "v"},
        ),
        registry,
        sandbox,
        {"read_only_tool": lambda _s, payload: (True, {"code": "ok", "echo": payload["value"]})},
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["echo"] == "v"


def test_write_safe_unchanged_requires_allow_write_safe(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _make_registry_and_sandbox(root)
    registry.register(
        ToolDefinition(
            name="write_safe_tool",
            description="Write-safe tool",
            permission_tier=PermissionTier.WRITE_SAFE,
            input_model=_WriteSafeInput,
        )
    )

    ok_denied, denied = execute_tool_call(
        ToolExecutionRequest(
            tool_name="write_safe_tool",
            payload={"path": "x"},
            allow_write_safe=False,
        ),
        registry,
        sandbox,
        {"write_safe_tool": lambda _s, _p: (True, {"code": "ok"})},
    )
    assert ok_denied is False
    assert denied["code"] == "permission_denied"
    assert denied["required_permission"] == PermissionTier.WRITE_SAFE.value

    ok_allowed, allowed = execute_tool_call(
        ToolExecutionRequest(
            tool_name="write_safe_tool",
            payload={"path": "x"},
            allow_write_safe=True,
        ),
        registry,
        sandbox,
        {"write_safe_tool": lambda _s, _p: (True, {"code": "ok"})},
    )
    assert ok_allowed is True
    assert allowed["code"] == "ok"
