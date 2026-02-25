"""Unit tests for Redis cache client wrapper (hermetic, no live Redis required)."""
from __future__ import annotations

from typing import Any

from backend.cache.redis_client import RedisCacheClient, create_default_redis_client


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
        # Minimal wildcard support for suffix "*" used by invalidate_pattern tests.
        if match.endswith("*"):
            prefix = match[:-1]
            for key in list(self._store.keys()):
                if key.startswith(prefix):
                    yield key
            return
        for key in list(self._store.keys()):
            if key == match:
                yield key


def _fake_factory(*_args: Any, **_kwargs: Any) -> _FakeRedis:
    return _FakeRedis()


def test_fail_safe_invalid_host_returns_none_false_without_raising() -> None:
    client = RedisCacheClient(url="redis://127.0.0.1:1/0", enabled=True, default_ttl=60)

    assert client.get("missing") is None
    assert client.set("k", "v") is False
    assert client.delete("k") is False
    assert client.invalidate_pattern("prefix:*") == 0
    assert client.get_json("missing") is None
    assert client.set_json("k", {"x": 1}) is False


def test_json_round_trip_with_injected_fake_redis() -> None:
    client = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        default_ttl=60,
        redis_factory=_fake_factory,
    )

    payload = {"foo": "bar", "count": 3}
    assert client.set_json("json:key", payload) is True
    assert client.get_json("json:key") == payload


def test_invalidate_pattern_with_injected_fake_redis() -> None:
    client = RedisCacheClient(
        url="redis://irrelevant:6379/0",
        enabled=True,
        default_ttl=60,
        redis_factory=_fake_factory,
    )

    assert client.set("ctx:1", "a") is True
    assert client.set("ctx:2", "b") is True
    assert client.set("other:1", "c") is True

    assert client.invalidate_pattern("ctx:*") == 2
    assert client.get("ctx:1") is None
    assert client.get("other:1") == "c"


def test_health_check_returns_stable_shape_for_disabled_unavailable_connected() -> None:
    disabled = RedisCacheClient(enabled=False)
    disabled_health = disabled.health_check()
    assert set(disabled_health.keys()) == {"enabled", "connected", "message"}
    assert disabled_health["enabled"] is False
    assert disabled_health["connected"] is False
    assert isinstance(disabled_health["message"], str)

    unavailable = RedisCacheClient(url="redis://127.0.0.1:1/0", enabled=True)
    unavailable_health = unavailable.health_check()
    assert set(unavailable_health.keys()) == {"enabled", "connected", "message"}
    assert unavailable_health["connected"] is False
    assert isinstance(unavailable_health["message"], str)

    connected = RedisCacheClient(enabled=True, redis_factory=_fake_factory)
    connected_health = connected.health_check()
    assert set(connected_health.keys()) == {"enabled", "connected", "message"}
    assert connected_health["enabled"] is True
    assert connected_health["connected"] is True
    assert connected_health["message"] == "Connected"


def test_create_default_redis_client_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("CACHE_ENABLED", "false")
    monkeypatch.setenv("CACHE_DEFAULT_TTL", "99")

    client = create_default_redis_client()
    assert client.enabled is False
    assert client.default_ttl == 99