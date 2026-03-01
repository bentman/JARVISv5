from __future__ import annotations

from backend.retrieval.retrieval_types import RetrievalConfig, RetrievalResult, SourceType
from backend.workflow.nodes.context_builder_node import ContextBuilderNode


class _MemoryManagerStub:
    def __init__(self, task: dict) -> None:
        self._task = task

    def get_task_state(self, _task_id: str) -> dict:
        return dict(self._task)


class _RetrieverStub:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = list(results)

    def retrieve(self, *_args, **_kwargs) -> list[RetrievalResult]:
        return list(self._results)


class _RaisingRetriever:
    def retrieve(self, *_args, **_kwargs) -> list[RetrievalResult]:
        raise RuntimeError("retrieval_failure")


def _make_result(
    *,
    source: SourceType,
    content: str,
    relevance: float,
    recency: float,
    config: RetrievalConfig,
) -> RetrievalResult:
    return RetrievalResult.from_scores(
        source=source,
        content=content,
        relevance_score=relevance,
        recency_score=recency,
        config=config,
    )


def test_context_builder_injects_retrieved_context_message_with_ordering() -> None:
    config = RetrievalConfig(max_results=3)
    retrieved = [
        _make_result(
            source=SourceType.SEMANTIC,
            content="semantic alpha",
            relevance=0.8,
            recency=0.5,
            config=config,
        ),
        _make_result(
            source=SourceType.EPISODIC,
            content="episodic beta",
            relevance=0.7,
            recency=0.6,
            config=config,
        ),
    ]

    node = ContextBuilderNode(
        retriever=_RetrieverStub(retrieved),
        retrieval_config=config,
        retrieval_message_max_chars=500,
    )
    context = {
        "memory_manager": _MemoryManagerStub(
            {
                "task_id": "task-1",
                "messages": [
                    {"role": "system", "content": "base-system"},
                    {"role": "user", "content": "hello"},
                ],
            }
        ),
        "task_id": "task-1",
        "turn": 2,
        "user_input": "hello",
    }

    result = node.execute(context)
    messages = result["messages"]

    assert messages[0] == {"role": "system", "content": "base-system"}
    assert messages[1]["role"] == "system"
    expected_block = (
        "Retrieved Context:\n"
        "- [semantic] score=0.710 semantic alpha\n"
        "- [episodic] score=0.670 episodic beta"
    )
    assert messages[1]["content"] == expected_block
    assert messages[2] == {"role": "user", "content": "hello"}


def test_context_builder_retrieval_fail_safe_on_exception() -> None:
    node = ContextBuilderNode(
        retriever=_RaisingRetriever(),
        retrieval_config=RetrievalConfig(max_results=3),
    )
    context = {
        "memory_manager": _MemoryManagerStub(
            {
                "task_id": "task-1",
                "messages": [
                    {"role": "user", "content": "unchanged"},
                ],
            }
        ),
        "task_id": "task-1",
        "turn": 1,
        "user_input": "query",
    }

    result = node.execute(context)

    assert result["messages"] == [{"role": "user", "content": "unchanged"}]


def test_context_builder_retrieval_injection_is_deterministic() -> None:
    config = RetrievalConfig(max_results=2)
    retrieved = [
        _make_result(
            source=SourceType.WORKING_STATE,
            content="same-content",
            relevance=0.9,
            recency=0.4,
            config=config,
        )
    ]

    node = ContextBuilderNode(
        retriever=_RetrieverStub(retrieved),
        retrieval_config=config,
        retrieval_message_max_chars=20,
    )
    base_context = {
        "memory_manager": _MemoryManagerStub(
            {
                "task_id": "task-1",
                "messages": [{"role": "user", "content": "hi"}],
            }
        ),
        "task_id": "task-1",
        "turn": 3,
        "user_input": "hi",
    }

    first = node.execute(dict(base_context))
    second = node.execute(dict(base_context))

    assert first["messages"][0] == second["messages"][0]
