from pathlib import Path

from backend.tools.file_tools import (
    DeleteFileInput,
    FileInfoInput,
    ListDirectoryInput,
    ReadFileInput,
    SearchFilesInput,
    WriteFileInput,
    register_core_file_tools,
    run_delete_file,
    run_file_info,
    run_list_directory,
    run_read_file,
    run_search_files,
    run_write_file,
)
from backend.tools.registry import ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig, SandboxErrorCode


def _make_sandbox(root: Path) -> Sandbox:
    return Sandbox(SandboxConfig(allowed_roots=(root,)))


def test_read_file_rejects_out_of_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    sandbox = _make_sandbox(root)
    ok, result = run_read_file(sandbox, ReadFileInput(path=str(outside)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_list_directory_rejects_out_of_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    sandbox = _make_sandbox(root)
    ok, result = run_list_directory(sandbox, ListDirectoryInput(path=str(outside_dir)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_file_info_rejects_out_of_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    sandbox = _make_sandbox(root)
    ok, result = run_file_info(sandbox, FileInfoInput(path=str(outside)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_write_file_rejects_out_of_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"

    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_write=True))
    ok, result = run_write_file(sandbox, WriteFileInput(path=str(outside), content="x"))

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_delete_file_rejects_out_of_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")

    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_delete=True))
    ok, result = run_delete_file(sandbox, DeleteFileInput(path=str(outside)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_in_root_read_list_info_succeed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    file_path = root / "alpha.txt"
    file_path.write_text("alpha", encoding="utf-8")

    sandbox = _make_sandbox(root)

    ok_read, read_res = run_read_file(sandbox, ReadFileInput(path=str(file_path)))
    assert ok_read is True
    assert read_res["code"] == "ok"
    assert read_res["content"] == "alpha"

    ok_list, list_res = run_list_directory(sandbox, ListDirectoryInput(path=str(root)))
    assert ok_list is True
    assert list_res["code"] == "ok"
    assert list_res["entries"] == ["alpha.txt"]

    ok_info, info_res = run_file_info(sandbox, FileInfoInput(path=str(file_path)))
    assert ok_info is True
    assert info_res["code"] == "ok"
    assert info_res["type"] == "file"
    assert info_res["size"] == 5


def test_registry_schema_export_and_validation_for_file_tools(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()

    registry = ToolRegistry()
    sandbox = _make_sandbox(root)
    register_core_file_tools(registry, sandbox)

    schemas = registry.export_all_schemas()
    assert [tool["name"] for tool in schemas] == [
        "delete_file",
        "file_info",
        "list_directory",
        "read_file",
        "search_files",
        "write_file",
    ]

    ok_read, payload_read = registry.validate_input(
        "read_file", {"path": "sample.txt", "encoding": "utf-8"}
    )
    assert ok_read is True
    assert payload_read == {"path": "sample.txt", "encoding": "utf-8"}

    ok_list, payload_list = registry.validate_input("list_directory", {})
    assert ok_list is False
    assert payload_list["code"] == "validation_error"


def test_write_file_denied_when_allow_write_false(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "note.txt"
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_write=False))

    ok, result = run_write_file(sandbox, WriteFileInput(path=str(target), content="abc"))

    assert ok is False
    assert result["code"] == SandboxErrorCode.WRITE_NOT_ALLOWED.value


def test_write_file_succeeds_when_allowed_within_limit(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "note.txt"
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_write=True, max_write_bytes=10))

    ok, result = run_write_file(
        sandbox,
        WriteFileInput(path=str(target), content="ab", encoding="utf-8"),
    )

    assert ok is True
    assert result["code"] == "ok"
    assert target.read_text(encoding="utf-8") == "ab"


def test_write_file_enforces_encoded_byte_limit(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "utf8.txt"
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_write=True, max_write_bytes=3))

    # "éé" is 4 bytes in UTF-8 (2 bytes each)
    ok, result = run_write_file(
        sandbox,
        WriteFileInput(path=str(target), content="éé", encoding="utf-8"),
    )

    assert ok is False
    assert result["code"] == SandboxErrorCode.WRITE_TOO_LARGE.value


def test_delete_file_denied_when_allow_delete_false(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "deleteme.txt"
    target.write_text("x", encoding="utf-8")
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_delete=False))

    ok, result = run_delete_file(sandbox, DeleteFileInput(path=str(target)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.DELETE_NOT_ALLOWED.value


def test_delete_file_succeeds_for_file_when_allowed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "deleteme.txt"
    target.write_text("x", encoding="utf-8")
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_delete=True))

    ok, result = run_delete_file(sandbox, DeleteFileInput(path=str(target)))

    assert ok is True
    assert result["code"] == "ok"
    assert not target.exists()


def test_delete_file_rejects_directory_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    directory = root / "dir"
    directory.mkdir()
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_delete=True))

    ok, result = run_delete_file(sandbox, DeleteFileInput(path=str(directory)))

    assert ok is False
    assert result["code"] == SandboxErrorCode.NOT_A_FILE.value


def test_search_files_rejects_out_of_root_root_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    sandbox = _make_sandbox(root)
    ok, result = run_search_files(
        sandbox,
        SearchFilesInput(root=str(outside_root), pattern="*.txt", max_results=10),
    )

    assert ok is False
    assert result["code"] == SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT.value


def test_search_files_returns_sorted_matches_and_respects_max_results(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "b.txt").write_text("b", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    sub = root / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("c", encoding="utf-8")
    (sub / "skip.md").write_text("m", encoding="utf-8")

    sandbox = _make_sandbox(root)
    ok, result = run_search_files(
        sandbox,
        SearchFilesInput(root=str(root), pattern="*.txt", max_results=2),
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["matches"] == ["a.txt", "b.txt"]
    assert result["count"] == 2
    assert result["truncated"] is True


def test_search_files_enforces_scan_cap(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    for idx in range(5):
        (root / f"f{idx}.txt").write_text("x", encoding="utf-8")

    sandbox = _make_sandbox(root)
    ok, result = sandbox.search_paths(root=str(root), pattern="*.txt", max_results=10, max_visited=2)

    assert ok is False
    assert result["code"] == SandboxErrorCode.SEARCH_LIMIT_EXCEEDED.value
