from pathlib import Path

from pydantic import BaseModel

from backend.cache.metrics import get_metrics
from backend.cache.redis_client import RedisCacheClient
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig


class _ReadOnlyInput(BaseModel):
    value: str


class _WriteSafeInput(BaseModel):
    value: str


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                deleted += 1
        return deleted

    def scan_iter(self, match: str):
        if match.endswith("*"):
            prefix = match[:-1]
            for key in list(self._store.keys()):
                if key.startswith(prefix):
                    yield key
            return
        for key in list(self._store.keys()):
            if key == match:
                yield key


def _fake_factory(*_args, **_kwargs) -> _FakeRedis:
    return _FakeRedis()


def _build_registry_and_sandbox(root: Path) -> tuple[ToolRegistry, Sandbox]:
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,), allow_write=True))
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="ro_tool",
            description="Read-only tool",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=_ReadOnlyInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="ws_tool",
            description="Write-safe tool",
            permission_tier=PermissionTier.WRITE_SAFE,
            input_model=_WriteSafeInput,
        )
    )
    return registry, sandbox


def test_cache_miss_then_hit_uses_cache_and_bypasses_handler(tmp_path: Path) -> None:
    get_metrics().reset()
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    cache = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        redis_factory=_fake_factory,
    )

    calls = {"count": 0}

    def _handler(_sandbox: Sandbox, payload: dict) -> tuple[bool, dict]:
        calls["count"] += 1
        return True, {"code": "ok", "echo": payload["value"], "calls": calls["count"]}

    request = ToolExecutionRequest(tool_name="ro_tool", payload={"value": "abc"})

    ok1, result1 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )
    assert ok1 is True
    assert result1["cache_hit"] is False
    assert result1["calls"] == 1
    assert calls["count"] == 1

    ok2, result2 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )
    assert ok2 is True
    assert result2["cache_hit"] is True
    assert result2["calls"] == 1
    assert calls["count"] == 1

    metrics = get_metrics().summary()
    assert metrics["categories"]["tool"]["hits"] == 1
    assert metrics["categories"]["tool"]["misses"] == 1
    assert metrics["sets"] == 1


def test_write_safe_tool_not_cached(tmp_path: Path) -> None:
    get_metrics().reset()
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    cache = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        redis_factory=_fake_factory,
    )

    calls = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        calls["count"] += 1
        return True, {"code": "ok", "calls": calls["count"]}

    request = ToolExecutionRequest(
        tool_name="ws_tool",
        payload={"value": "abc"},
        allow_write_safe=True,
    )

    ok1, result1 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ws_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )
    ok2, result2 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ws_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )

    assert ok1 is True and ok2 is True
    assert "cache_hit" not in result1
    assert "cache_hit" not in result2
    assert calls["count"] == 2


def test_enable_caching_false_bypasses_cache_even_with_client(tmp_path: Path) -> None:
    get_metrics().reset()
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    cache = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        redis_factory=_fake_factory,
    )

    calls = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        calls["count"] += 1
        return True, {"code": "ok", "calls": calls["count"]}

    request = ToolExecutionRequest(tool_name="ro_tool", payload={"value": "abc"})

    ok1, result1 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=False,
    )
    ok2, result2 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=False,
    )

    assert ok1 is True and ok2 is True
    assert "cache_hit" not in result1
    assert "cache_hit" not in result2
    assert calls["count"] == 2


def test_cache_disabled_via_env_bypasses_cache_without_breaking_execution(monkeypatch, tmp_path: Path) -> None:
    get_metrics().reset()
    monkeypatch.setenv("CACHE_ENABLED", "off")
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    cache = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        redis_factory=_fake_factory,
    )

    calls = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        calls["count"] += 1
        return True, {"code": "ok", "calls": calls["count"]}

    request = ToolExecutionRequest(tool_name="ro_tool", payload={"value": "abc"})

    ok1, result1 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )
    ok2, result2 = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"ro_tool": _handler},
        cache_client=cache,
        enable_caching=True,
    )

    assert ok1 is True and ok2 is True
    assert "cache_hit" not in result1
    assert "cache_hit" not in result2
    assert calls["count"] == 2
