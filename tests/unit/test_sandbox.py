from pathlib import Path

from backend.tools.sandbox import Sandbox, SandboxConfig


def _make_sandbox(root: Path, **kwargs) -> Sandbox:
    config = SandboxConfig(allowed_roots=(root,), **kwargs)
    return Sandbox(config)


def test_resolve_blocks_parent_traversal_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sandbox = _make_sandbox(root)

    ok, result = sandbox.resolve_in_sandbox(root / ".." / "outside.txt")
    assert ok is False
    assert result["code"] == "path_outside_allowed_root"


def test_resolve_blocks_absolute_path_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sandbox = _make_sandbox(root)

    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")

    ok, result = sandbox.resolve_in_sandbox(outside)
    assert ok is False
    assert result["code"] == "path_outside_allowed_root"


def test_resolve_in_root_succeeds(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "file.txt"
    inside.write_text("hello", encoding="utf-8")
    sandbox = _make_sandbox(root)

    ok, result = sandbox.resolve_in_sandbox(inside)
    assert ok is True
    assert result["code"] == "ok"
    assert result["path"] == str(inside.resolve())


def test_read_text_success_and_limit_enforced(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sandbox = _make_sandbox(root, max_read_bytes=3)

    small = root / "small.txt"
    small.write_text("abc", encoding="utf-8")
    ok_small, res_small = sandbox.read_text(small)
    assert ok_small is True
    assert res_small["content"] == "abc"

    large = root / "large.txt"
    large.write_text("abcd", encoding="utf-8")
    ok_large, res_large = sandbox.read_text(large)
    assert ok_large is False
    assert res_large["code"] == "read_too_large"


def test_write_denied_when_toggle_false(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sandbox = _make_sandbox(root, allow_write=False)

    ok, result = sandbox.write_text(root / "w.txt", "abc")
    assert ok is False
    assert result["code"] == "write_not_allowed"


def test_delete_denied_when_toggle_false(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "d.txt"
    target.write_text("abc", encoding="utf-8")
    sandbox = _make_sandbox(root, allow_delete=False)

    ok, result = sandbox.delete_path(target)
    assert ok is False
    assert result["code"] == "delete_not_allowed"


def test_write_size_limit_enforced(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sandbox = _make_sandbox(root, allow_write=True, max_write_bytes=3)

    ok, result = sandbox.write_text(root / "w.txt", "abcd")
    assert ok is False
    assert result["code"] == "write_too_large"


def test_list_dir_success_and_deterministic_order(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "b.txt").write_text("b", encoding="utf-8")
    (root / "a.txt").write_text("a", encoding="utf-8")
    sandbox = _make_sandbox(root, max_list_entries=10)

    ok, result = sandbox.list_dir(root)
    assert ok is True
    assert result["entries"] == ["a.txt", "b.txt"]
