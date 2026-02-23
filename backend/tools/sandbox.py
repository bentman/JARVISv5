from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxConfig:
    allowed_roots: tuple[Path, ...]
    max_read_bytes: int = 1_000_000
    max_write_bytes: int = 1_000_000
    allow_write: bool = False
    allow_delete: bool = False
    max_list_entries: int = 1_000


class SandboxErrorCode(str, Enum):
    INVALID_PATH = "invalid_path"
    PATH_OUTSIDE_ALLOWED_ROOT = "path_outside_allowed_root"
    NOT_FOUND = "not_found"
    NOT_A_FILE = "not_a_file"
    NOT_A_DIRECTORY = "not_a_directory"
    READ_TOO_LARGE = "read_too_large"
    WRITE_TOO_LARGE = "write_too_large"
    WRITE_NOT_ALLOWED = "write_not_allowed"
    DELETE_NOT_ALLOWED = "delete_not_allowed"
    LIST_LIMIT_EXCEEDED = "list_limit_exceeded"
    SEARCH_LIMIT_EXCEEDED = "search_limit_exceeded"
    IO_ERROR = "io_error"


class Sandbox:
    def __init__(self, config: SandboxConfig) -> None:
        normalized_roots = tuple(sorted((root.resolve() for root in config.allowed_roots), key=str))
        self.config = SandboxConfig(
            allowed_roots=normalized_roots,
            max_read_bytes=config.max_read_bytes,
            max_write_bytes=config.max_write_bytes,
            allow_write=config.allow_write,
            allow_delete=config.allow_delete,
            max_list_entries=config.max_list_entries,
        )

    def _is_under_allowed_root(self, candidate: Path) -> bool:
        for root in self.config.allowed_roots:
            try:
                candidate.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _error(self, code: SandboxErrorCode, message: str, **extra: Any) -> tuple[bool, dict[str, Any]]:
        payload: dict[str, Any] = {"code": code.value, "message": message}
        payload.update(extra)
        return False, payload

    def resolve_in_sandbox(self, path: str | Path) -> tuple[bool, dict[str, Any]]:
        try:
            raw_path = Path(path)
        except TypeError:
            return self._error(SandboxErrorCode.INVALID_PATH, "Invalid path type")

        if raw_path.exists():
            candidate = raw_path.resolve()
            if not self._is_under_allowed_root(candidate):
                return self._error(
                    SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT,
                    "Resolved path is outside allowed roots",
                    path=str(raw_path),
                )
            return True, {"code": "ok", "path": str(candidate)}

        try:
            parent = raw_path.parent if raw_path.parent != Path("") else Path(".")
            resolved_parent = parent.resolve(strict=True)
        except FileNotFoundError:
            return self._error(
                SandboxErrorCode.NOT_FOUND,
                "Parent directory not found",
                path=str(raw_path),
            )
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"Failed to resolve parent: {exc}", path=str(raw_path))

        if not self._is_under_allowed_root(resolved_parent):
            return self._error(
                SandboxErrorCode.PATH_OUTSIDE_ALLOWED_ROOT,
                "Resolved parent path is outside allowed roots",
                path=str(raw_path),
            )

        candidate = (resolved_parent / raw_path.name).resolve(strict=False)
        return True, {"code": "ok", "path": str(candidate)}

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> tuple[bool, dict[str, Any]]:
        ok, resolved_or_error = self.resolve_in_sandbox(path)
        if not ok:
            return False, resolved_or_error

        resolved = Path(resolved_or_error["path"])
        if not resolved.exists():
            return self._error(SandboxErrorCode.NOT_FOUND, "Path does not exist", path=str(path))
        if not resolved.is_file():
            return self._error(SandboxErrorCode.NOT_A_FILE, "Path is not a file", path=str(path))

        try:
            size = resolved.stat().st_size
            if size > self.config.max_read_bytes:
                return self._error(
                    SandboxErrorCode.READ_TOO_LARGE,
                    "File exceeds max_read_bytes",
                    size=size,
                    max_read_bytes=self.config.max_read_bytes,
                )

            content = resolved.read_text(encoding=encoding)
            return True, {"code": "ok", "path": str(resolved), "content": content, "size": size}
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"Read failed: {exc}", path=str(path))

    def list_dir(self, path: str | Path) -> tuple[bool, dict[str, Any]]:
        ok, resolved_or_error = self.resolve_in_sandbox(path)
        if not ok:
            return False, resolved_or_error

        resolved = Path(resolved_or_error["path"])
        if not resolved.exists():
            return self._error(SandboxErrorCode.NOT_FOUND, "Path does not exist", path=str(path))
        if not resolved.is_dir():
            return self._error(SandboxErrorCode.NOT_A_DIRECTORY, "Path is not a directory", path=str(path))

        try:
            entries = sorted(item.name for item in resolved.iterdir())
            if len(entries) > self.config.max_list_entries:
                return self._error(
                    SandboxErrorCode.LIST_LIMIT_EXCEEDED,
                    "Directory exceeds max_list_entries",
                    count=len(entries),
                    max_list_entries=self.config.max_list_entries,
                )
            return True, {"code": "ok", "path": str(resolved), "entries": entries}
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"List failed: {exc}", path=str(path))

    def file_info(self, path: str | Path) -> tuple[bool, dict[str, Any]]:
        ok, resolved_or_error = self.resolve_in_sandbox(path)
        if not ok:
            return False, resolved_or_error

        resolved = Path(resolved_or_error["path"])
        if not resolved.exists():
            return self._error(SandboxErrorCode.NOT_FOUND, "Path does not exist", path=str(path))

        try:
            stat = resolved.stat()
            if resolved.is_file():
                item_type = "file"
            elif resolved.is_dir():
                item_type = "directory"
            else:
                item_type = "other"

            return True, {
                "code": "ok",
                "path": str(resolved),
                "type": item_type,
                "size": stat.st_size,
                "modified_epoch": stat.st_mtime,
            }
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"File info failed: {exc}", path=str(path))

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8") -> tuple[bool, dict[str, Any]]:
        if not self.config.allow_write:
            return self._error(SandboxErrorCode.WRITE_NOT_ALLOWED, "Write operation is disabled")

        content_size = len(content.encode(encoding))
        if content_size > self.config.max_write_bytes:
            return self._error(
                SandboxErrorCode.WRITE_TOO_LARGE,
                "Content exceeds max_write_bytes",
                size=content_size,
                max_write_bytes=self.config.max_write_bytes,
            )

        ok, resolved_or_error = self.resolve_in_sandbox(path)
        if not ok:
            return False, resolved_or_error

        resolved = Path(resolved_or_error["path"])
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding=encoding)
            return True, {"code": "ok", "path": str(resolved), "size": content_size}
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"Write failed: {exc}", path=str(path))

    def delete_path(self, path: str | Path) -> tuple[bool, dict[str, Any]]:
        if not self.config.allow_delete:
            return self._error(SandboxErrorCode.DELETE_NOT_ALLOWED, "Delete operation is disabled")

        ok, resolved_or_error = self.resolve_in_sandbox(path)
        if not ok:
            return False, resolved_or_error

        resolved = Path(resolved_or_error["path"])
        if not resolved.exists():
            return self._error(SandboxErrorCode.NOT_FOUND, "Path does not exist", path=str(path))
        if not resolved.is_file():
            return self._error(SandboxErrorCode.NOT_A_FILE, "Delete supports files only", path=str(path))

        try:
            resolved.unlink()
            return True, {"code": "ok", "path": str(resolved)}
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"Delete failed: {exc}", path=str(path))

    def search_paths(
        self,
        root: str | Path,
        pattern: str,
        max_results: int,
        max_visited: int = 20_000,
    ) -> tuple[bool, dict[str, Any]]:
        ok, resolved_or_error = self.resolve_in_sandbox(root)
        if not ok:
            return False, resolved_or_error

        resolved_root = Path(resolved_or_error["path"])
        if not resolved_root.exists():
            return self._error(SandboxErrorCode.NOT_FOUND, "Path does not exist", path=str(root))
        if not resolved_root.is_dir():
            return self._error(SandboxErrorCode.NOT_A_DIRECTORY, "Path is not a directory", path=str(root))

        try:
            visited = 0
            matched: list[str] = []
            truncated = False

            stack: list[Path] = [resolved_root]
            while stack:
                current = stack.pop()
                children = sorted(current.iterdir(), key=lambda p: p.name)
                for entry in children:
                    rel = entry.relative_to(resolved_root).as_posix()

                    visited += 1
                    if visited > max_visited:
                        return self._error(
                            SandboxErrorCode.SEARCH_LIMIT_EXCEEDED,
                            "Search exceeded max_visited entries",
                            max_visited=max_visited,
                        )

                    if fnmatch.fnmatch(rel, pattern):
                        if len(matched) < max_results:
                            matched.append(rel)
                        else:
                            truncated = True

                    if entry.is_dir():
                        stack.append(entry)

                stack.sort(key=lambda p: p.as_posix(), reverse=True)

            return True, {
                "code": "ok",
                "root": str(resolved_root),
                "pattern": pattern,
                "matches": matched,
                "count": len(matched),
                "truncated": truncated,
            }
        except OSError as exc:
            return self._error(SandboxErrorCode.IO_ERROR, f"Search failed: {exc}", path=str(root))
