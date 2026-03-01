from __future__ import annotations

from datetime import datetime, timezone
from math import exp
from typing import Any, Callable

from backend.retrieval.retrieval_types import RetrievalConfig, RetrievalResult, SourceType


class HybridRetriever:
    def __init__(
        self,
        *,
        semantic_store: Any,
        episodic_memory: Any,
        working_state_provider: Callable[[str], dict[str, Any] | None],
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.semantic_store = semantic_store
        self.episodic_memory = episodic_memory
        self.working_state_provider = working_state_provider
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def retrieve(
        self,
        query: str,
        *,
        task_id: str | None,
        turn: int | None,
        config: RetrievalConfig,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        del turn  # reserved for future retrieval policy tuning

        query_text = query.strip()
        if not query_text:
            raise ValueError("query must be non-empty")

        requested_limit = int(limit)
        if requested_limit < 1:
            raise ValueError("limit must be >= 1")

        cap = min(requested_limit, config.max_results)
        candidate_pool = max(cap, config.max_results)

        results: list[RetrievalResult] = []
        results.extend(self._retrieve_working_state(query_text, task_id, config))
        results.extend(self._retrieve_semantic(query_text, task_id, config, candidate_pool))
        results.extend(self._retrieve_episodic(query_text, task_id, config, candidate_pool))

        filtered = [
            item
            for item in results
            if item.final_score >= config.min_final_score_threshold
        ]

        ordered = self._rank_deterministically(filtered)
        return ordered[:cap]

    def _retrieve_working_state(
        self,
        query: str,
        task_id: str | None,
        config: RetrievalConfig,
    ) -> list[RetrievalResult]:
        if not task_id:
            return []

        task = self.working_state_provider(task_id)
        if not isinstance(task, dict):
            return []

        raw_messages = task.get("messages", [])
        if not isinstance(raw_messages, list):
            return []

        messages = [
            msg for msg in raw_messages[-config.working_state_window :] if isinstance(msg, dict)
        ]
        if not messages:
            return []

        query_lower = query.lower()
        newest_index = len(messages) - 1
        results: list[RetrievalResult] = []
        for idx, message in enumerate(messages):
            content = str(message.get("content", ""))
            content_lower = content.lower()
            is_match = query_lower in content_lower
            relevance = (
                config.working_state_match_relevance
                if is_match
                else config.working_state_nomatch_relevance
            )
            age = newest_index - idx
            recency = self._decay_from_steps(age, config.ws_decay_tau)

            results.append(
                RetrievalResult.from_scores(
                    source=SourceType.WORKING_STATE,
                    content=content,
                    relevance_score=relevance,
                    recency_score=recency,
                    config=config,
                    task_id=task_id,
                    metadata={
                        "role": str(message.get("role", "")),
                        "position": idx,
                    },
                )
            )

        return results

    def _retrieve_semantic(
        self,
        query: str,
        task_id: str | None,
        config: RetrievalConfig,
        candidate_pool: int,
    ) -> list[RetrievalResult]:
        rows = self.semantic_store.search_text(query, top_k=candidate_pool)
        results: list[RetrievalResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            metadata = row.get("metadata", {})
            metadata_dict = metadata if isinstance(metadata, dict) else {}
            timestamp = metadata_dict.get("timestamp")
            recency = self._timestamp_recency(
                timestamp,
                default_score=config.semantic_recency_default,
                tau_hours=config.time_decay_tau_hours,
            )

            results.append(
                RetrievalResult.from_scores(
                    source=SourceType.SEMANTIC,
                    content=str(row.get("text", "")),
                    relevance_score=float(row.get("similarity_score", 0.0)),
                    recency_score=recency,
                    config=config,
                    task_id=task_id,
                    timestamp=timestamp if isinstance(timestamp, str) else None,
                    metadata={
                        "vector_id": row.get("vector_id"),
                        "distance": row.get("distance"),
                        **metadata_dict,
                    },
                )
            )
        return results

    def _retrieve_episodic(
        self,
        query: str,
        task_id: str | None,
        config: RetrievalConfig,
        candidate_pool: int,
    ) -> list[RetrievalResult]:
        results: list[RetrievalResult] = []

        decisions = self.episodic_memory.search_decisions(
            query,
            limit=candidate_pool,
            task_id=task_id,
        )
        for row in decisions:
            if not isinstance(row, dict):
                continue
            timestamp = row.get("timestamp")
            recency = self._timestamp_recency(
                timestamp,
                default_score=config.episodic_recency_default,
                tau_hours=config.time_decay_tau_hours,
            )
            results.append(
                RetrievalResult.from_scores(
                    source=SourceType.EPISODIC,
                    content=str(row.get("content", "")),
                    relevance_score=config.episodic_decision_relevance,
                    recency_score=recency,
                    config=config,
                    task_id=str(row.get("task_id")) if row.get("task_id") is not None else task_id,
                    timestamp=timestamp if isinstance(timestamp, str) else None,
                    metadata={
                        "kind": "decision",
                        "id": row.get("id"),
                        "action_type": row.get("action_type"),
                        "status": row.get("status"),
                    },
                )
            )

        tool_calls = self.episodic_memory.search_tool_calls(
            query,
            limit=candidate_pool,
            task_id=task_id,
        )
        for row in tool_calls:
            if not isinstance(row, dict):
                continue
            timestamp = row.get("timestamp")
            recency = self._timestamp_recency(
                timestamp,
                default_score=config.episodic_recency_default,
                tau_hours=config.time_decay_tau_hours,
            )
            content = f"{row.get('tool_name', '')} {row.get('params', '')} {row.get('result', '')}".strip()
            results.append(
                RetrievalResult.from_scores(
                    source=SourceType.EPISODIC,
                    content=content,
                    relevance_score=config.episodic_toolcall_relevance,
                    recency_score=recency,
                    config=config,
                    task_id=str(row.get("task_id")) if row.get("task_id") is not None else task_id,
                    timestamp=timestamp if isinstance(timestamp, str) else None,
                    metadata={
                        "kind": "tool_call",
                        "id": row.get("id"),
                        "decision_id": row.get("decision_id"),
                        "tool_name": row.get("tool_name"),
                        "params": row.get("params"),
                        "result": row.get("result"),
                    },
                )
            )

        return results

    @staticmethod
    def _decay_from_steps(age_steps: int, tau: float) -> float:
        age = max(0, int(age_steps))
        score = exp(-float(age) / float(tau))
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    def _timestamp_recency(self, timestamp: Any, *, default_score: float, tau_hours: float) -> float:
        if not isinstance(timestamp, str) or not timestamp.strip():
            return default_score
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            now = self.now_provider()
            if now.tzinfo is None:
                now = now.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (now - parsed).total_seconds())
            age_hours = age_seconds / 3600.0
            return self._decay_from_steps(int(age_hours * 1000), tau_hours * 1000.0)
        except Exception:
            return default_score

    @staticmethod
    def _stable_id(result: RetrievalResult) -> int:
        for key in ("vector_id", "id", "decision_id", "position"):
            value = result.metadata.get(key)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        return 2**31 - 1

    def _rank_deterministically(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        source_priority = {
            SourceType.WORKING_STATE: 0,
            SourceType.SEMANTIC: 1,
            SourceType.EPISODIC: 2,
        }
        return sorted(
            results,
            key=lambda item: (
                -float(item.final_score),
                source_priority.get(item.source, 99),
                self._stable_id(item),
                item.content,
            ),
        )
