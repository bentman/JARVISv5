"""Unit tests for ContextBuilderNode cache behavior (M6.4)."""
from __future__ import annotations

import tempfile
from pathlib import Path

from backend.cache.key_policy import make_cache_key
from backend.cache.metrics import get_metrics
from backend.cache.redis_client import RedisCacheClient
from backend.memory.memory_manager import MemoryManager
from backend.workflow.nodes.context_builder_node import ContextBuilderNode


class _TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


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


def _build_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=_TestEmbeddingFunction(),
    )


def _reset_metrics() -> None:
    get_metrics().reset()


def test_context_builder_cache_hit_uses_cached_messages_and_records_hit() -> None:
    _reset_metrics()
    try:
        cache = RedisCacheClient(
            url="redis://irrelevant:6379/0",
            enabled=True,
            redis_factory=_fake_factory,
        )
        node = ContextBuilderNode(cache_client=cache)

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = _build_memory(tmp_dir)
            memory.create_task("cache-task", "goal", ["step"])

            key = make_cache_key("context", parts={"task_id": "cache-task", "turn": 1})
            assert cache.set_json(
                key,
                {"messages": [{"role": "assistant", "content": "from-cache"}]},
                ttl=3600,
            )

            context = {"memory_manager": memory, "task_id": "cache-task", "turn": 1}
            result = node.execute(context)

            assert result["cache_hit"] is True
            assert result["messages"] == [{"role": "assistant", "content": "from-cache"}]
            assert result["working_state"]["task_id"] == "cache-task"

            metrics = get_metrics().summary()
            assert metrics["hits"] == 1
            assert metrics["misses"] == 0
            assert metrics["categories"]["context"]["hits"] == 1
    finally:
        _reset_metrics()


def test_context_builder_cache_miss_builds_messages_writes_cache_and_records_miss() -> None:
    _reset_metrics()
    try:
        cache = RedisCacheClient(
            url="redis://irrelevant:6379/0",
            enabled=True,
            redis_factory=_fake_factory,
        )
        node = ContextBuilderNode(cache_client=cache)

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = _build_memory(tmp_dir)
            memory.create_task("miss-task", "goal", ["step"])
            memory.append_task_message("miss-task", "user", "hello")

            context = {"memory_manager": memory, "task_id": "miss-task", "turn": 2}
            result = node.execute(context)

            assert result["cache_hit"] is False
            assert result["messages"] == [{"role": "user", "content": "hello"}]

            key = make_cache_key("context", parts={"task_id": "miss-task", "turn": 2})
            cached = cache.get_json(key)
            assert cached == {"messages": [{"role": "user", "content": "hello"}]}

            metrics = get_metrics().summary()
            assert metrics["hits"] == 0
            assert metrics["misses"] == 1
            assert metrics["categories"]["context"]["misses"] == 1
    finally:
        _reset_metrics()


def test_context_builder_fail_safe_when_cache_unavailable_still_builds_context() -> None:
    _reset_metrics()
    try:
        unavailable_cache = RedisCacheClient(url="redis://127.0.0.1:1/0", enabled=True)
        node = ContextBuilderNode(cache_client=unavailable_cache)

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = _build_memory(tmp_dir)
            memory.create_task("safe-task", "goal", ["step"])
            memory.append_task_message("safe-task", "user", "fallback")

            context = {"memory_manager": memory, "task_id": "safe-task", "turn": 3}
            result = node.execute(context)

            assert result["messages"] == [{"role": "user", "content": "fallback"}]
            assert result["cache_hit"] is False
            assert result["working_state"]["task_id"] == "safe-task"
    finally:
        _reset_metrics()


def test_context_builder_cache_disabled_via_env_still_builds_context(monkeypatch) -> None:
    _reset_metrics()
    monkeypatch.setenv("CACHE_ENABLED", "false")
    try:
        cache = RedisCacheClient(
            url="redis://irrelevant:6379/0",
            enabled=True,
            redis_factory=_fake_factory,
        )
        node = ContextBuilderNode(cache_client=cache)

        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = _build_memory(tmp_dir)
            memory.create_task("disabled-task", "goal", ["step"])
            memory.append_task_message("disabled-task", "user", "no-cache")

            context = {"memory_manager": memory, "task_id": "disabled-task", "turn": 4}
            result = node.execute(context)

            assert result["messages"] == [{"role": "user", "content": "no-cache"}]
            assert result["cache_hit"] is False
            key = make_cache_key("context", parts={"task_id": "disabled-task", "turn": 4})
            assert cache.get_json(key) is None
    finally:
        _reset_metrics()
