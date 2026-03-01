from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.retrieval_types import RetrievalConfig, SourceType


class _SemanticStub:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def search_text(self, query: str, top_k: int = 5) -> list[dict]:
        del query
        return list(self.rows[:top_k])


class _EpisodicStub:
    def __init__(self, decisions: list[dict], tool_calls: list[dict]) -> None:
        self.decisions = decisions
        self.tool_calls = tool_calls

    def search_decisions(self, query: str, *, limit: int = 20, task_id: str | None = None) -> list[dict]:
        del query
        rows = [row for row in self.decisions if task_id is None or row.get("task_id") == task_id]
        return rows[:limit]

    def search_tool_calls(self, query: str, *, limit: int = 20, task_id: str | None = None) -> list[dict]:
        del query
        rows = [row for row in self.tool_calls if task_id is None or row.get("task_id") == task_id]
        return rows[:limit]


def test_hybrid_retriever_deterministic_ranking_mixed_sources() -> None:
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    semantic = _SemanticStub(
        [
            {
                "text": "semantic tie",
                "metadata": {},
                "vector_id": 10,
                "distance": 0.0,
                "similarity_score": 0.9,
            }
        ]
    )
    episodic = _EpisodicStub(decisions=[], tool_calls=[])
    working_state = {
        "messages": [
            {"role": "user", "content": "query context"},
        ]
    }

    retriever = HybridRetriever(
        semantic_store=semantic,
        episodic_memory=episodic,
        working_state_provider=lambda task_id: working_state if task_id == "task-1" else None,
        now_provider=lambda: fixed_now,
    )

    config = RetrievalConfig(
        relevance_weight=1.0,
        recency_weight=0.0,
        semantic_recency_default=0.5,
        working_state_match_relevance=0.9,
        working_state_nomatch_relevance=0.4,
        min_final_score_threshold=0.0,
        max_results=10,
    )

    results = retriever.retrieve(
        "query",
        task_id="task-1",
        turn=1,
        config=config,
        limit=10,
    )

    assert len(results) == 2
    # equal final score -> source priority tie-break puts working_state first
    assert [item.source for item in results] == [SourceType.WORKING_STATE, SourceType.SEMANTIC]


def test_hybrid_retriever_recency_decay_with_fixed_now() -> None:
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    newer = (fixed_now - timedelta(hours=1)).isoformat()
    older = (fixed_now - timedelta(hours=48)).isoformat()

    semantic = _SemanticStub([])
    episodic = _EpisodicStub(
        decisions=[
            {
                "id": 1,
                "timestamp": older,
                "task_id": "task-1",
                "action_type": "plan",
                "content": "older decision",
                "status": "done",
            },
            {
                "id": 2,
                "timestamp": newer,
                "task_id": "task-1",
                "action_type": "plan",
                "content": "newer decision",
                "status": "done",
            },
        ],
        tool_calls=[],
    )

    retriever = HybridRetriever(
        semantic_store=semantic,
        episodic_memory=episodic,
        working_state_provider=lambda _task_id: {"messages": []},
        now_provider=lambda: fixed_now,
    )

    config = RetrievalConfig(
        relevance_weight=0.0,
        recency_weight=1.0,
        episodic_decision_relevance=0.5,
        min_final_score_threshold=0.0,
        max_results=10,
    )

    results = retriever.retrieve(
        "decision",
        task_id="task-1",
        turn=1,
        config=config,
        limit=10,
    )

    assert len(results) == 2
    assert results[0].content == "newer decision"
    assert results[0].recency_score > results[1].recency_score


def test_hybrid_retriever_respects_threshold_and_max_results() -> None:
    semantic = _SemanticStub(
        [
            {"text": "a", "metadata": {}, "vector_id": 1, "distance": 0.0, "similarity_score": 0.9},
            {"text": "b", "metadata": {}, "vector_id": 2, "distance": 0.0, "similarity_score": 0.7},
            {"text": "c", "metadata": {}, "vector_id": 3, "distance": 0.0, "similarity_score": 0.4},
        ]
    )
    episodic = _EpisodicStub(decisions=[], tool_calls=[])

    retriever = HybridRetriever(
        semantic_store=semantic,
        episodic_memory=episodic,
        working_state_provider=lambda _task_id: {"messages": []},
    )

    config = RetrievalConfig(
        relevance_weight=1.0,
        recency_weight=0.0,
        min_final_score_threshold=0.6,
        max_results=2,
    )

    results = retriever.retrieve(
        "semantic",
        task_id="task-1",
        turn=1,
        config=config,
        limit=10,
    )

    assert [item.content for item in results] == ["a", "b"]


def test_hybrid_retriever_rejects_empty_query() -> None:
    retriever = HybridRetriever(
        semantic_store=_SemanticStub([]),
        episodic_memory=_EpisodicStub(decisions=[], tool_calls=[]),
        working_state_provider=lambda _task_id: {"messages": []},
    )

    with pytest.raises(ValueError):
        retriever.retrieve(
            "   ",
            task_id="task-1",
            turn=1,
            config=RetrievalConfig(),
            limit=5,
        )
