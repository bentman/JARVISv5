## Milestone 4 — Tool System + Sandboxed Execution

> This document is a conceptual reference for tool system architecture and local assistant tools.
> Use this as a guideline and design reference; it is not a copy-paste implementation playbook.

### Why this follows DAG + baseline harness
Tools introduce side effects; deterministic orchestration and replay instrumentation must be in place first to keep behavior auditable and fail-closed.

### Deliverables
- JSON-schema tool registry
- Permission tiers and constrained execution boundaries
- Tool-call workflow node with explicit IO contracts
- Core Local Tools (`read_file`, `write_file`, `list_directory`, `file_info`, `search_files`)
- System Information Tools (`get_timestamp`, `get_system_info`, `get_working_directory`)

### Essential for daily use:
- `read_file` - Read text file contents
- `write_file` - Write text to file
- `list_directory` - List files in directory
- `file_info` - Get file metadata (size, modified, etc.)
- `search_files` - Find files by pattern

Useful for context:
- `get_timestamp` - Current date/time
- `get_system_info` - OS, Python version, etc.
- `get_working_directory` - Current directory

**Project.md citations:** §3.4, §5.1 (`tool_call`), §8.2

---

# JARVISv5 Tool System Implementation Guide - Milestone 4

**Objective**: Implement tool registry, sandboxed execution, and core local tools for daily-use file operations.

---

## Architecture Overview

```
User: "Read file.txt and summarize it"
  ↓
Router → intent=code/file_ops
  ↓
DAG: [tool_call(read_file) → llm_worker(summarize)]
  ↓
tool_call_node:
  - Lookup tool in registry
  - Validate parameters against schema
  - Execute in sandbox
  - Return result
  ↓
llm_worker: Gets file contents in context, generates summary
  ↓
User sees: Summary of file.txt
```

---

## Tool Categories

### **Tier 1: File Operations** (Milestone 4 Core)
Essential for daily use:
- `read_file` - Read text file contents
- `write_file` - Write text to file
- `list_directory` - List files in directory
- `file_info` - Get file metadata (size, modified, etc.)
- `search_files` - Find files by pattern

### **Tier 2: System Information** (Milestone 4 Extended)
Useful for context:
- `get_timestamp` - Current date/time
- `get_system_info` - OS, Python version, etc.
- `get_working_directory` - Current directory

### **Tier 3: Code Execution** (Future - Post Milestone 5 Security)
Requires sandboxing:
- `execute_python` - Run Python code
- `execute_shell` - Run shell command

### **Tier 4: Web/Search** (Milestone 8)
External access:
- `search_web` - Web search
- `fetch_url` - Download web page

### **Tier 5: Memory Operations** (Future)
Direct memory access:
- `search_memory` - Query semantic memory
- `add_knowledge` - Store fact in semantic memory

---

## Implementation Tasks

### Task 4.1: Tool Registry Foundation

**File**: `backend/tools/registry.py`

**Purpose**: Central registry for tool definitions with JSON schema validation.

**Implementation**:

```python
"""
Tool Registry - Central registration and schema validation for tools
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError


class PermissionTier(str, Enum):
    """Security permission levels for tools"""
    READ_ONLY = "read_only"      # Can read files/data
    WRITE_SAFE = "write_safe"    # Can write to allowed directories
    SYSTEM = "system"            # Can execute code/commands


class ToolParameter(BaseModel):
    """Parameter definition for a tool"""
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    pattern: str | None = None  # Regex for string validation
    min_value: int | float | None = None
    max_value: int | float | None = None


class ToolDefinition(BaseModel):
    """Complete tool definition with schema"""
    id: str = Field(..., description="Unique tool identifier")
    name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="What the tool does")
    permission_tier: PermissionTier
    parameters: list[ToolParameter]
    returns: str = Field(..., description="Description of return value")
    examples: list[str] = Field(default_factory=list)
    enabled: bool = True


class ToolRegistry:
    """Central registry for tool definitions and implementations"""
    
    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}
        self.implementations: dict[str, Callable] = {}
    
    def register(
        self,
        tool_def: ToolDefinition,
        implementation: Callable
    ) -> None:
        """Register a tool with its definition and implementation"""
        if tool_def.id in self.tools:
            raise ValueError(f"Tool already registered: {tool_def.id}")
        
        self.tools[tool_def.id] = tool_def
        self.implementations[tool_def.id] = implementation
    
    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        """Get tool definition by ID"""
        return self.tools.get(tool_id)
    
    def get_implementation(self, tool_id: str) -> Callable | None:
        """Get tool implementation function"""
        return self.implementations.get(tool_id)
    
    def list_tools(
        self,
        permission_tier: PermissionTier | None = None,
        enabled_only: bool = True
    ) -> list[ToolDefinition]:
        """List all registered tools, optionally filtered"""
        tools = list(self.tools.values())
        
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        
        if permission_tier:
            tools = [t for t in tools if t.permission_tier == permission_tier]
        
        return tools
    
    def validate_parameters(
        self,
        tool_id: str,
        parameters: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate parameters against tool schema"""
        tool_def = self.get_tool(tool_id)
        if not tool_def:
            return False, f"Tool not found: {tool_id}"
        
        # Check required parameters
        for param in tool_def.parameters:
            if param.required and param.name not in parameters:
                return False, f"Missing required parameter: {param.name}"
        
        # Validate parameter types and constraints
        for param_name, param_value in parameters.items():
            param_def = next(
                (p for p in tool_def.parameters if p.name == param_name),
                None
            )
            
            if not param_def:
                return False, f"Unknown parameter: {param_name}"
            
            # Type validation
            valid, error = self._validate_type(
                param_value,
                param_def.type,
                param_def
            )
            if not valid:
                return False, f"Parameter {param_name}: {error}"
        
        return True, ""
    
    def _validate_type(
        self,
        value: Any,
        expected_type: str,
        param_def: ToolParameter
    ) -> tuple[bool, str]:
        """Validate parameter type and constraints"""
        if expected_type == "string":
            if not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"
            
            if param_def.pattern:
                import re
                if not re.match(param_def.pattern, value):
                    return False, f"Does not match pattern: {param_def.pattern}"
        
        elif expected_type == "integer":
            if not isinstance(value, int):
                return False, f"Expected integer, got {type(value).__name__}"
            
            if param_def.min_value is not None and value < param_def.min_value:
                return False, f"Below minimum: {param_def.min_value}"
            
            if param_def.max_value is not None and value > param_def.max_value:
                return False, f"Above maximum: {param_def.max_value}"
        
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"
        
        elif expected_type == "array":
            if not isinstance(value, list):
                return False, f"Expected array, got {type(value).__name__}"
        
        elif expected_type == "object":
            if not isinstance(value, dict):
                return False, f"Expected object, got {type(value).__name__}"
        
        return True, ""
    
    def to_json_schema(self, tool_id: str) -> dict[str, Any] | None:
        """Export tool definition as JSON schema for LLM"""
        tool_def = self.get_tool(tool_id)
        if not tool_def:
            return None
        
        properties = {}
        required = []
        
        for param in tool_def.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            
            if param.pattern:
                prop["pattern"] = param.pattern
            
            if param.min_value is not None:
                prop["minimum"] = param.min_value
            
            if param.max_value is not None:
                prop["maximum"] = param.max_value
            
            if param.default is not None:
                prop["default"] = param.default
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": tool_def.id,
            "description": tool_def.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


# Global registry instance
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    return _global_registry
```

**Validation**:
```bash
# Test registry
python -c "
from backend.tools.registry import get_registry, ToolDefinition, ToolParameter, PermissionTier

registry = get_registry()

# Register test tool
test_tool = ToolDefinition(
    id='test_tool',
    name='Test Tool',
    description='A test tool',
    permission_tier=PermissionTier.READ_ONLY,
    parameters=[
        ToolParameter(name='input', type='string', description='Test input')
    ],
    returns='Test output'
)

registry.register(test_tool, lambda input: f'Processed: {input}')

# Validate
valid, error = registry.validate_parameters('test_tool', {'input': 'hello'})
print(f'Valid: {valid}, Error: {error}')
"
```

---

### Task 4.2: Sandbox Execution

**File**: `backend/tools/sandbox.py`

**Purpose**: Isolated execution environment with resource limits and path constraints.

**Implementation**:

```python
"""
Sandbox - Secure, isolated tool execution with resource limits
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class SandboxError(Exception):
    """Sandbox execution error"""
    pass


class Sandbox:
    """Execution sandbox with security constraints"""
    
    def __init__(
        self,
        allowed_read_paths: list[str] | None = None,
        allowed_write_paths: list[str] | None = None,
        timeout_seconds: int = 30,
        max_output_size: int = 10_000_000  # 10MB
    ):
        self.allowed_read_paths = [
            Path(p).resolve() for p in (allowed_read_paths or [])
        ]
        self.allowed_write_paths = [
            Path(p).resolve() for p in (allowed_write_paths or [])
        ]
        self.timeout_seconds = timeout_seconds
        self.max_output_size = max_output_size
    
    def validate_read_path(self, path: str | Path) -> Path:
        """Validate path is allowed for reading"""
        resolved = Path(path).resolve()
        
        # Check if path is under any allowed directory
        for allowed in self.allowed_read_paths:
            try:
                resolved.relative_to(allowed)
                return resolved
            except ValueError:
                continue
        
        raise SandboxError(
            f"Path not in allowed read directories: {path}\n"
            f"Allowed: {[str(p) for p in self.allowed_read_paths]}"
        )
    
    def validate_write_path(self, path: str | Path) -> Path:
        """Validate path is allowed for writing"""
        resolved = Path(path).resolve()
        
        for allowed in self.allowed_write_paths:
            try:
                resolved.relative_to(allowed)
                return resolved
            except ValueError:
                continue
        
        raise SandboxError(
            f"Path not in allowed write directories: {path}\n"
            f"Allowed: {[str(p) for p in self.allowed_write_paths]}"
        )
    
    def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file with path validation"""
        validated_path = self.validate_read_path(path)
        
        if not validated_path.exists():
            raise SandboxError(f"File not found: {path}")
        
        if not validated_path.is_file():
            raise SandboxError(f"Not a file: {path}")
        
        try:
            content = validated_path.read_text(encoding=encoding)
            
            if len(content) > self.max_output_size:
                raise SandboxError(
                    f"File too large: {len(content)} bytes "
                    f"(max: {self.max_output_size})"
                )
            
            return content
        except UnicodeDecodeError as e:
            raise SandboxError(f"File encoding error: {e}")
    
    def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8"
    ) -> None:
        """Write file with path validation"""
        validated_path = self.validate_write_path(path)
        
        if len(content) > self.max_output_size:
            raise SandboxError(
                f"Content too large: {len(content)} bytes "
                f"(max: {self.max_output_size})"
            )
        
        # Create parent directories if needed
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        
        validated_path.write_text(content, encoding=encoding)
    
    def list_directory(self, path: str) -> list[dict[str, Any]]:
        """List directory contents with metadata"""
        validated_path = self.validate_read_path(path)
        
        if not validated_path.exists():
            raise SandboxError(f"Directory not found: {path}")
        
        if not validated_path.is_dir():
            raise SandboxError(f"Not a directory: {path}")
        
        items = []
        for item in sorted(validated_path.iterdir()):
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": item.stat().st_mtime
            })
        
        return items
    
    def execute_python(self, code: str) -> tuple[str, str, int]:
        """Execute Python code in subprocess (future implementation)"""
        # Placeholder for future implementation after security review
        raise NotImplementedError("Code execution requires additional security review")


def create_default_sandbox() -> Sandbox:
    """Create sandbox with default JARVISv5 paths"""
    # Allow reading from common project directories
    read_paths = [
        ".",  # Project root
        str(Path.home()),  # User home
    ]
    
    # Allow writing only to data and temporary directories
    write_paths = [
        "data",
        tempfile.gettempdir()
    ]
    
    return Sandbox(
        allowed_read_paths=read_paths,
        allowed_write_paths=write_paths,
        timeout_seconds=30,
        max_output_size=10_000_000
    )
```

**Validation**:
```bash
# Test sandbox
python -c "
from backend.tools.sandbox import create_default_sandbox

sandbox = create_default_sandbox()

# Test path validation
try:
    path = sandbox.validate_read_path('README.md')
    print(f'Valid read path: {path}')
except Exception as e:
    print(f'Error: {e}')

# Test forbidden path
try:
    sandbox.validate_write_path('/etc/passwd')
    print('ERROR: Should have blocked /etc/passwd')
except Exception as e:
    print(f'Correctly blocked: {e}')
"
```

---

### Task 4.3: Core File Tools

**File**: `backend/tools/implementations/file_ops.py`

**Purpose**: Implement core file operation tools.

**Implementation**:

```python
"""
File Operations Tools - Core tools for file system access
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.tools.registry import (
    ToolDefinition,
    ToolParameter,
    PermissionTier,
    get_registry
)
from backend.tools.sandbox import Sandbox


def register_file_tools(sandbox: Sandbox) -> None:
    """Register all file operation tools"""
    registry = get_registry()
    
    # read_file
    registry.register(
        ToolDefinition(
            id="read_file",
            name="Read File",
            description="Read the complete contents of a text file",
            permission_tier=PermissionTier.READ_ONLY,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                )
            ],
            returns="File contents as string",
            examples=[
                "read_file path='README.md'",
                "read_file path='data/notes.txt' encoding='utf-8'"
            ]
        ),
        lambda path, encoding="utf-8": _read_file_impl(sandbox, path, encoding)
    )
    
    # write_file
    registry.register(
        ToolDefinition(
            id="write_file",
            name="Write File",
            description="Write text content to a file, creating or overwriting",
            permission_tier=PermissionTier.WRITE_SAFE,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path where file should be written",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Text content to write",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                )
            ],
            returns="Success message with file path",
            examples=[
                "write_file path='output.txt' content='Hello World'",
                "write_file path='data/report.md' content='# Report\\n\\nContent here'"
            ]
        ),
        lambda path, content, encoding="utf-8": _write_file_impl(
            sandbox, path, content, encoding
        )
    )
    
    # list_directory
    registry.register(
        ToolDefinition(
            id="list_directory",
            name="List Directory",
            description="List all files and subdirectories in a directory",
            permission_tier=PermissionTier.READ_ONLY,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to directory to list",
                    required=True
                )
            ],
            returns="List of items with name, type, size, modified time",
            examples=[
                "list_directory path='.'",
                "list_directory path='data'"
            ]
        ),
        lambda path: _list_directory_impl(sandbox, path)
    )
    
    # file_info
    registry.register(
        ToolDefinition(
            id="file_info",
            name="File Info",
            description="Get detailed metadata about a file or directory",
            permission_tier=PermissionTier.READ_ONLY,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to file or directory",
                    required=True
                )
            ],
            returns="Metadata including size, type, modified time, permissions",
            examples=[
                "file_info path='README.md'",
                "file_info path='data'"
            ]
        ),
        lambda path: _file_info_impl(sandbox, path)
    )
    
    # search_files
    registry.register(
        ToolDefinition(
            id="search_files",
            name="Search Files",
            description="Find files matching a pattern in a directory tree",
            permission_tier=PermissionTier.READ_ONLY,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Directory to search in",
                    required=True
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern or regex to match filenames",
                    required=True
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Search subdirectories recursively",
                    required=False,
                    default=True
                )
            ],
            returns="List of matching file paths",
            examples=[
                "search_files directory='.' pattern='*.py'",
                "search_files directory='backend' pattern='test_*.py' recursive=True"
            ]
        ),
        lambda directory, pattern, recursive=True: _search_files_impl(
            sandbox, directory, pattern, recursive
        )
    )


def _read_file_impl(sandbox: Sandbox, path: str, encoding: str) -> str:
    """Implementation of read_file tool"""
    return sandbox.read_file(path, encoding)


def _write_file_impl(
    sandbox: Sandbox,
    path: str,
    content: str,
    encoding: str
) -> str:
    """Implementation of write_file tool"""
    sandbox.write_file(path, content, encoding)
    return f"Successfully wrote {len(content)} characters to {path}"


def _list_directory_impl(sandbox: Sandbox, path: str) -> str:
    """Implementation of list_directory tool"""
    items = sandbox.list_directory(path)
    
    # Format as readable output
    lines = [f"Contents of {path}:"]
    for item in items:
        type_marker = "[DIR]" if item["type"] == "directory" else "[FILE]"
        size_str = f"{item['size']:,} bytes" if item["type"] == "file" else ""
        lines.append(f"  {type_marker} {item['name']} {size_str}")
    
    return "\n".join(lines)


def _file_info_impl(sandbox: Sandbox, path: str) -> str:
    """Implementation of file_info tool"""
    validated_path = sandbox.validate_read_path(path)
    
    if not validated_path.exists():
        return f"File not found: {path}"
    
    stat = validated_path.stat()
    
    info_lines = [
        f"Path: {path}",
        f"Type: {'Directory' if validated_path.is_dir() else 'File'}",
        f"Size: {stat.st_size:,} bytes",
        f"Modified: {stat.st_mtime}",
        f"Permissions: {oct(stat.st_mode)[-3:]}"
    ]
    
    return "\n".join(info_lines)


def _search_files_impl(
    sandbox: Sandbox,
    directory: str,
    pattern: str,
    recursive: bool
) -> str:
    """Implementation of search_files tool"""
    validated_dir = sandbox.validate_read_path(directory)
    
    if not validated_dir.exists():
        return f"Directory not found: {directory}"
    
    if not validated_dir.is_dir():
        return f"Not a directory: {directory}"
    
    # Use glob for pattern matching
    if recursive:
        matches = list(validated_dir.rglob(pattern))
    else:
        matches = list(validated_dir.glob(pattern))
    
    if not matches:
        return f"No files matching '{pattern}' in {directory}"
    
    lines = [f"Found {len(matches)} matching files:"]
    for match in sorted(matches):
        lines.append(f"  {match}")
    
    return "\n".join(lines)
```

**Validation**:
```bash
# Test file tools
python -c "
from backend.tools.sandbox import create_default_sandbox
from backend.tools.implementations.file_ops import register_file_tools
from backend.tools.registry import get_registry

# Setup
sandbox = create_default_sandbox()
register_file_tools(sandbox)
registry = get_registry()

# List tools
tools = registry.list_tools()
print(f'Registered {len(tools)} file tools:')
for tool in tools:
    print(f'  - {tool.id}: {tool.description}')
"
```

---

### Task 4.4: Tool Call Workflow Node

**File**: `backend/workflow/nodes/tool_call_node.py`

**Purpose**: Execute tool calls from workflow with registry lookup and sandbox execution.

**Implementation**:

```python
"""
Tool Call Node - Executes tool calls within workflow
"""
from __future__ import annotations

from typing import Any

from backend.tools.registry import get_registry
from backend.tools.sandbox import Sandbox, SandboxError
from .base_node import BaseNode


class ToolCallNode(BaseNode):
    """Workflow node that executes tool calls"""
    
    def __init__(self, sandbox: Sandbox | None = None):
        self.sandbox = sandbox
        self.registry = get_registry()
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute tool call from context
        
        Expected context:
        {
            "tool_id": "read_file",
            "tool_parameters": {"path": "README.md"},
            ...
        }
        
        Adds to context:
        {
            "tool_output": "file contents...",
            "tool_error": "error message" (if failed),
            "tool_success": True/False
        }
        """
        tool_id = context.get("tool_id")
        tool_parameters = context.get("tool_parameters", {})
        
        if not tool_id:
            context["tool_error"] = "No tool_id specified"
            context["tool_success"] = False
            return context
        
        # Get tool definition
        tool_def = self.registry.get_tool(tool_id)
        if not tool_def:
            context["tool_error"] = f"Tool not found: {tool_id}"
            context["tool_success"] = False
            return context
        
        if not tool_def.enabled:
            context["tool_error"] = f"Tool is disabled: {tool_id}"
            context["tool_success"] = False
            return context
        
        # Validate parameters
        valid, error = self.registry.validate_parameters(tool_id, tool_parameters)
        if not valid:
            context["tool_error"] = f"Parameter validation failed: {error}"
            context["tool_success"] = False
            return context
        
        # Get implementation
        impl = self.registry.get_implementation(tool_id)
        if not impl:
            context["tool_error"] = f"Tool implementation not found: {tool_id}"
            context["tool_success"] = False
            return context
        
        # Execute tool
        try:
            result = impl(**tool_parameters)
            context["tool_output"] = str(result)
            context["tool_success"] = True
            context["tool_error"] = None
        except SandboxError as e:
            context["tool_error"] = f"Sandbox error: {e}"
            context["tool_success"] = False
        except Exception as e:
            context["tool_error"] = f"Tool execution error: {e}"
            context["tool_success"] = False
        
        return context
```

**Test**: `tests/unit/test_tool_call_node.py`

```python
"""
Unit tests for ToolCallNode
"""
import pytest
from backend.workflow.nodes.tool_call_node import ToolCallNode
from backend.tools.sandbox import create_default_sandbox
from backend.tools.implementations.file_ops import register_file_tools
from backend.tools.registry import get_registry


@pytest.fixture
def setup_tools():
    """Setup tool registry for tests"""
    sandbox = create_default_sandbox()
    register_file_tools(sandbox)
    return sandbox


def test_tool_call_node_read_file(setup_tools, tmp_path):
    """Test ToolCallNode executes read_file correctly"""
    sandbox = setup_tools
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World")
    
    # Execute node
    node = ToolCallNode(sandbox)
    context = {
        "tool_id": "read_file",
        "tool_parameters": {"path": str(test_file)}
    }
    
    result = node.execute(context)
    
    assert result["tool_success"] is True
    assert result["tool_output"] == "Hello World"
    assert result["tool_error"] is None


def test_tool_call_node_invalid_tool(setup_tools):
    """Test ToolCallNode handles invalid tool ID"""
    sandbox = setup_tools
    node = ToolCallNode(sandbox)
    
    context = {
        "tool_id": "nonexistent_tool",
        "tool_parameters": {}
    }
    
    result = node.execute(context)
    
    assert result["tool_success"] is False
    assert "not found" in result["tool_error"]


def test_tool_call_node_invalid_parameters(setup_tools):
    """Test ToolCallNode validates parameters"""
    sandbox = setup_tools
    node = ToolCallNode(sandbox)
    
    context = {
        "tool_id": "read_file",
        "tool_parameters": {}  # Missing required 'path' parameter
    }
    
    result = node.execute(context)
    
    assert result["tool_success"] is False
    assert "validation failed" in result["tool_error"].lower()
```

**Validation**:
```bash
pytest tests/unit/test_tool_call_node.py -v
```

---

### Task 4.5: Wire Tools into Controller

**File**: `backend/controller/controller_service.py` (additions)

**Purpose**: Integrate ToolCallNode into workflow execution.

**Implementation**:

```python
# Add to imports
from backend.tools.sandbox import create_default_sandbox
from backend.tools.implementations.file_ops import register_file_tools
from backend.workflow.nodes.tool_call_node import ToolCallNode

class ControllerService:
    def __init__(
        self,
        memory_manager: MemoryManager | None = None,
        hardware_service: HardwareService | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self.memory = memory_manager or MemoryManager()
        self.hardware = hardware_service or HardwareService()
        self.registry = model_registry or ModelRegistry()
        
        # Initialize tool sandbox
        self.sandbox = create_default_sandbox()
        register_file_tools(self.sandbox)
    
    def run(self, user_input: str, task_id: str | None = None, ...) -> dict[str, Any]:
        # ... existing code ...
        
        # Add tool_call_node to node registry
        tool_call_node = ToolCallNode(self.sandbox)
        
        # Update DAG compiler to include tool nodes when detected
        # (Router can set intent=file_ops, compiler adds tool_call node)
```

**Note**: Full integration requires updating plan compiler to detect tool usage and insert tool_call nodes into DAG.

---

## Summary of Deliverables

### Created Files

1. **`backend/tools/registry.py`** - Tool registry with schema validation
2. **`backend/tools/sandbox.py`** - Sandboxed execution environment
3. **`backend/tools/implementations/file_ops.py`** - 5 core file tools
4. **`backend/workflow/nodes/tool_call_node.py`** - Tool execution node
5. **`tests/unit/test_tool_call_node.py`** - Unit tests

### Tool Inventory

| Tool ID | Permission | Description |
|---------|-----------|-------------|
| `read_file` | READ_ONLY | Read text file contents |
| `write_file` | WRITE_SAFE | Write text to file |
| `list_directory` | READ_ONLY | List directory contents |
| `file_info` | READ_ONLY | Get file metadata |
| `search_files` | READ_ONLY | Find files by pattern |

### Validation Commands

```bash
# Unit tests
pytest tests/unit/test_tool_call_node.py -v

# Integration test
python -c "
from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager

memory = MemoryManager()
service = ControllerService(memory_manager=memory)

# Test tool call via controller
result = service.run(
    user_input='Read the README.md file',
    tool_id='read_file',
    tool_parameters={'path': 'README.md'}
)

print(f'Tool output: {result[\"context\"].get(\"tool_output\", \"N/A\")}')
"

# Full validation
python scripts/validate_backend.py --scope integration
```

---

## Next Steps After Milestone 4

With tools working:

1. **Update LLM prompt** to include tool schemas
2. **Parse LLM output** for tool call requests
3. **Router enhancement** to detect file operation intents
4. **Plan compiler** to generate tool-augmented DAGs
5. **UI indication** when tool is executing

This enables: "Read project.md and summarize it" → Actually reads file → LLM summarizes contents.