from __future__ import annotations

from typing import Any

from backend.cache.key_policy import make_cache_key
from backend.cache.metrics import get_metrics
from backend.cache.redis_client import RedisCacheClient
from backend.cache.settings import load_cache_settings
from backend.retrieval.retrieval_types import RetrievalConfig

from .base_node import BaseNode


class ContextBuilderNode(BaseNode):
    def __init__(
        self,
        cache_client: RedisCacheClient | None = None,
        retriever: Any | None = None,
        retrieval_config: RetrievalConfig | None = None,
        retrieval_message_max_chars: int = 500,
        retrieval_token_budget: int = 600,
    ) -> None:
        self.cache = cache_client
        self.metrics = get_metrics()
        settings = load_cache_settings()
        self.cache_enabled = settings.cache_enabled
        self.context_cache_ttl_seconds = settings.context_cache_ttl_seconds
        self.retriever = retriever
        self.retrieval_config = retrieval_config
        self.retrieval_message_max_chars = max(1, int(retrieval_message_max_chars))
        self.retrieval_token_budget = max(1, int(retrieval_token_budget))

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        context["retrieved_context_injected"] = []
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

        try:
            messages = self._inject_attachment_context(messages, context)
        except Exception:
            pass

        try:
            messages, retrieved_context_injected = self._inject_retrieved_context(
                messages,
                context,
                task_id,
                turn,
            )
            context["retrieved_context_injected"] = retrieved_context_injected
        except Exception:
            pass

        context["messages"] = messages
        context["cache_hit"] = cache_hit
        return context

    def _inject_attachment_context(
        self,
        messages: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        user_input = str(context.get("user_input", ""))
        begin_marker = "[ATTACHMENT_CONTEXT_BEGIN]"
        end_marker = "[ATTACHMENT_CONTEXT_END]"
        begin_index = user_input.find(begin_marker)
        end_index = user_input.find(end_marker)
        if begin_index < 0 or end_index <= begin_index:
            return messages

        attachment_block = user_input[begin_index + len(begin_marker) : end_index].strip()
        if not attachment_block:
            return messages

        attachment_lines = [line for line in attachment_block.splitlines() if line.strip()]
        if not attachment_lines:
            return messages

        filename = "attachment"
        if attachment_lines[0].startswith("filename="):
            filename = attachment_lines[0].split("=", 1)[1].strip() or "attachment"
            attachment_lines = attachment_lines[1:]

        attachment_text = "\n".join(attachment_lines).strip()
        if not attachment_text:
            return messages
        if len(attachment_text) > 1200:
            attachment_text = f"{attachment_text[:1200]}..."

        attachment_message = {
            "role": "system",
            "content": f"Attachment Context ({filename}):\n{attachment_text}",
        }

        output = list(messages)
        insert_at = 0
        for idx, message in enumerate(output):
            if str(message.get("role", "")) == "system":
                insert_at = idx + 1
                break
        output.insert(insert_at, attachment_message)
        return output

    def _inject_retrieved_context(
        self,
        messages: list[dict[str, Any]],
        context: dict[str, Any],
        task_id: Any,
        turn: int,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if self.retriever is None:
            return messages, []

        query_text = str(context.get("user_input", "")).strip()
        if not query_text:
            return messages, []

        config = self.retrieval_config or RetrievalConfig()
        results = self.retriever.retrieve(
            query_text,
            task_id=str(task_id) if task_id else None,
            turn=turn,
            config=config,
            limit=config.max_results,
        )
        if not results:
            return messages, []

        lines = ["Retrieved Context:"]
        used_tokens = _approx_token_count(lines[0])
        for result in results:
            content = str(result.content)
            if len(content) > self.retrieval_message_max_chars:
                content = f"{content[: self.retrieval_message_max_chars]}..."
            line = f"- [{result.source.value}] score={float(result.final_score):.3f} {content}"
            line_tokens = _approx_token_count(line)
            if used_tokens + line_tokens > self.retrieval_token_budget:
                break
            lines.append(line)
            used_tokens += line_tokens

        if len(lines) == 1:
            return messages, []

        retrieval_message = {"role": "system", "content": "\n".join(lines)}

        output = list(messages)
        insert_at = 0
        for idx, message in enumerate(output):
            if str(message.get("role", "")) == "system":
                insert_at = idx + 1
                break

        output.insert(insert_at, retrieval_message)
        return output, [str(retrieval_message["content"])]


def _approx_token_count(text: str) -> int:
    value = str(text or "")
    if not value:
        return 0
    # Deterministic approximation: ~4 chars per token.
    return max(1, (len(value) + 3) // 4)
