from __future__ import annotations

from typing import Any

from backend.cache.key_policy import make_cache_key
from backend.cache.metrics import get_metrics
from backend.cache.redis_client import RedisCacheClient
from backend.cache.settings import load_cache_settings

from .base_node import BaseNode


class ContextBuilderNode(BaseNode):
    def __init__(self, cache_client: RedisCacheClient | None = None) -> None:
        self.cache = cache_client
        self.metrics = get_metrics()
        settings = load_cache_settings()
        self.cache_enabled = settings.cache_enabled
        self.context_cache_ttl_seconds = settings.context_cache_ttl_seconds

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        memory_manager = context.get("memory_manager")
        task_id = context.get("task_id")

        if memory_manager is None:
            context["working_state"] = None
            context["context_builder_error"] = "memory_manager_missing"
            return context

        if not task_id:
            context["working_state"] = None
            context["context_builder_error"] = "task_id_missing"
            return context

        working_state = memory_manager.get_task_state(str(task_id))
        context["working_state"] = working_state

        turn_raw = context.get("turn", 0)
        try:
            turn = int(turn_raw)
        except (TypeError, ValueError):
            turn = 0

        cache_attempted = False
        cache_hit = False
        cache_key: str | None = None
        messages: list[dict[str, Any]] = []

        if self.cache_enabled and self.cache is not None:
            try:
                cache_key = make_cache_key(
                    "context",
                    parts={"task_id": str(task_id), "turn": turn},
                )
                cache_attempted = True
                cached_payload = self.cache.get_json(cache_key)
                if isinstance(cached_payload, dict):
                    raw_cached_messages = cached_payload.get("messages", [])
                    if isinstance(raw_cached_messages, list):
                        messages = [msg for msg in raw_cached_messages if isinstance(msg, dict)][-10:]
                    else:
                        messages = []
                    cache_hit = True
                    self.metrics.record_hit("context")
            except Exception:
                cache_key = None

        if not cache_hit:
            if cache_attempted:
                self.metrics.record_miss("context")

            if isinstance(working_state, dict):
                raw_messages = working_state.get("messages", [])
                if isinstance(raw_messages, list):
                    messages = [msg for msg in raw_messages if isinstance(msg, dict)][-10:]

            if self.cache_enabled and self.cache is not None and cache_key is not None:
                try:
                    self.cache.set_json(
                        cache_key,
                        {"messages": messages},
                        ttl=self.context_cache_ttl_seconds,
                    )
                except Exception:
                    pass

        context["messages"] = messages
        context["cache_hit"] = cache_hit
        return context
