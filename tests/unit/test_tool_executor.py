from pathlib import Path

from pydantic import BaseModel

from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.file_tools import build_file_tool_dispatch_map, register_core_file_tools
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig


def _build_registry_and_sandbox(root: Path, *, allow_write: bool = False) -> tuple[ToolRegistry, Sandbox]:
    sandbox = Sandbox(
        SandboxConfig(
            allowed_roots=(root,),
            allow_write=allow_write,
        )
    )
    registry = ToolRegistry()
    register_core_file_tools(registry, sandbox)
    return registry, sandbox


def test_execute_tool_call_unknown_tool_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    ok, result = execute_tool_call(
        ToolExecutionRequest(tool_name="missing_tool", payload={}),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
    )

    assert ok is False
    assert result["code"] == "tool_not_found"


def test_execute_tool_call_validation_error_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    ok, result = execute_tool_call(
        ToolExecutionRequest(tool_name="read_file", payload={}),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
    )

    assert ok is False
    assert result["code"] == "validation_error"


def test_execute_tool_call_permission_denied_for_write_safe(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root, allow_write=True)

    target = root / "note.txt"
    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="write_file",
            payload={"path": str(target), "content": "abc", "encoding": "utf-8"},
            allow_write_safe=False,
        ),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
    )

    assert ok is False
    assert result["code"] == "permission_denied"


def test_execute_tool_call_read_only_success(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    registry, sandbox = _build_registry_and_sandbox(root)

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="list_directory",
            payload={"path": str(root)},
        ),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["entries"] == ["a.txt"]


def test_execute_tool_call_write_safe_success_with_flag(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root, allow_write=True)

    target = root / "note.txt"
    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="write_file",
            payload={"path": str(target), "content": "abc", "encoding": "utf-8"},
            allow_write_safe=True,
        ),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
    )

    assert ok is True
    assert result["code"] == "ok"
    assert target.read_text(encoding="utf-8") == "abc"


def test_execute_tool_call_missing_dispatch_handler(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    ok, result = execute_tool_call(
        ToolExecutionRequest(
            tool_name="read_file",
            payload={"path": str(root / "a.txt")},
        ),
        registry,
        sandbox,
        {},
    )

    assert ok is False
    assert result["code"] == "tool_not_implemented"


def test_execute_tool_call_execution_error_when_handler_raises(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    def _boom(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        raise RuntimeError("boom")

    ok, result = execute_tool_call(
        ToolExecutionRequest(tool_name="read_file", payload={"path": str(root / "a.txt")}),
        registry,
        sandbox,
        {"read_file": _boom},
    )

    assert ok is False
    assert result["code"] == "execution_error"


def test_execute_tool_call_system_permission_denied(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    class SystemInput(BaseModel):
        value: str

    registry.register(
        ToolDefinition(
            name="system_tool",
            description="System restricted tool",
            permission_tier=PermissionTier.SYSTEM,
            input_model=SystemInput,
        )
    )

    ok, result = execute_tool_call(
        ToolExecutionRequest(tool_name="system_tool", payload={"value": "x"}, allow_write_safe=True),
        registry,
        sandbox,
        {"system_tool": lambda _s, _p: (True, {"code": "ok"})},
    )

    assert ok is False
    assert result["code"] == "permission_denied"
