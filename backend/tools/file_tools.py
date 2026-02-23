from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox


class ReadFileInput(BaseModel):
    path: str = Field(min_length=1)
    encoding: str = "utf-8"


class ListDirectoryInput(BaseModel):
    path: str = Field(min_length=1)


class FileInfoInput(BaseModel):
    path: str = Field(min_length=1)


class WriteFileInput(BaseModel):
    path: str = Field(min_length=1)
    content: str
    encoding: str = "utf-8"


class DeleteFileInput(BaseModel):
    path: str = Field(min_length=1)


class SearchFilesInput(BaseModel):
    root: str = Field(min_length=1)
    pattern: str = Field(min_length=1)
    max_results: int = Field(default=100, ge=1, le=1000)


def run_read_file(sandbox: Sandbox, payload: ReadFileInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.read_text(path=payload.path, encoding=payload.encoding)


def run_list_directory(sandbox: Sandbox, payload: ListDirectoryInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.list_dir(path=payload.path)


def run_file_info(sandbox: Sandbox, payload: FileInfoInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.file_info(path=payload.path)


def run_write_file(sandbox: Sandbox, payload: WriteFileInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.write_text(path=payload.path, content=payload.content, encoding=payload.encoding)


def run_delete_file(sandbox: Sandbox, payload: DeleteFileInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.delete_path(path=payload.path)


def run_search_files(sandbox: Sandbox, payload: SearchFilesInput) -> tuple[bool, dict[str, Any]]:
    return sandbox.search_paths(root=payload.root, pattern=payload.pattern, max_results=payload.max_results)


def build_file_tool_dispatch_map() -> dict[str, Any]:
    return {
        "read_file": lambda sandbox, payload: run_read_file(sandbox, ReadFileInput.model_validate(payload)),
        "list_directory": lambda sandbox, payload: run_list_directory(
            sandbox, ListDirectoryInput.model_validate(payload)
        ),
        "file_info": lambda sandbox, payload: run_file_info(sandbox, FileInfoInput.model_validate(payload)),
        "write_file": lambda sandbox, payload: run_write_file(sandbox, WriteFileInput.model_validate(payload)),
        "delete_file": lambda sandbox, payload: run_delete_file(sandbox, DeleteFileInput.model_validate(payload)),
        "search_files": lambda sandbox, payload: run_search_files(
            sandbox, SearchFilesInput.model_validate(payload)
        ),
    }


def register_core_file_tools(registry: ToolRegistry, sandbox: Sandbox) -> None:
    """Register M4.3 core file tools in the schema registry."""
    _ = sandbox
    registry.register(
        ToolDefinition(
            name="read_file",
            description="Read text file contents within sandbox roots",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=ReadFileInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="list_directory",
            description="List directory entries within sandbox roots",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=ListDirectoryInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="file_info",
            description="Return file metadata within sandbox roots",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=FileInfoInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="write_file",
            description="Write text file contents within sandbox roots",
            permission_tier=PermissionTier.WRITE_SAFE,
            input_model=WriteFileInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="delete_file",
            description="Delete a file within sandbox roots",
            permission_tier=PermissionTier.WRITE_SAFE,
            input_model=DeleteFileInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="search_files",
            description="Search file paths by glob pattern within sandbox roots",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=SearchFilesInput,
        )
    )
