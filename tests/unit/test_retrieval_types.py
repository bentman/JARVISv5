import pytest

from backend.retrieval.retrieval_types import (
    RetrievalConfig,
    RetrievalResult,
    SourceType,
    compute_final_score,
    rank_results,
)


def test_compute_final_score_weighted_math_is_deterministic() -> None:
    config = RetrievalConfig(relevance_weight=0.8, recency_weight=0.2)

    score = compute_final_score(0.75, 0.25, config)

    assert score == pytest.approx(0.65)


def test_compute_final_score_clamps_input_boundaries() -> None:
    config = RetrievalConfig(relevance_weight=0.6, recency_weight=0.4)

    score = compute_final_score(-0.5, 1.5, config)

    # clamped inputs become relevance=0.0 and recency=1.0
    assert score == pytest.approx(0.4)
    assert 0.0 <= score <= 1.0


def test_weight_changes_alter_final_score_as_expected() -> None:
    relevance_favored = RetrievalConfig(relevance_weight=0.9, recency_weight=0.1)
    recency_favored = RetrievalConfig(relevance_weight=0.1, recency_weight=0.9)

    score_rel = compute_final_score(0.9, 0.2, relevance_favored)
    score_rec = compute_final_score(0.9, 0.2, recency_favored)

    assert score_rel > score_rec


def test_retrieval_result_from_scores_computes_final_score() -> None:
    config = RetrievalConfig(relevance_weight=0.7, recency_weight=0.3)

    result = RetrievalResult.from_scores(
        source=SourceType.SEMANTIC,
        content="semantic result",
        relevance_score=1.2,
        recency_score=-0.2,
        config=config,
        metadata={"task_id": "task-1"},
    )

    assert result.relevance_score == pytest.approx(1.0)
    assert result.recency_score == pytest.approx(0.0)
    assert result.final_score == pytest.approx(0.7)


def test_rank_results_stable_for_equal_scores() -> None:
    config = RetrievalConfig(relevance_weight=0.5, recency_weight=0.5)
    a = RetrievalResult.from_scores(
        source=SourceType.WORKING_STATE,
        content="a",
        relevance_score=0.6,
        recency_score=0.6,
        config=config,
        metadata={"id": "a"},
    )
    b = RetrievalResult.from_scores(
        source=SourceType.SEMANTIC,
        content="b",
        relevance_score=0.6,
        recency_score=0.6,
        config=config,
        metadata={"id": "b"},
    )
    c = RetrievalResult.from_scores(
        source=SourceType.EPISODIC,
        content="c",
        relevance_score=0.9,
        recency_score=0.9,
        config=config,
        metadata={"id": "c"},
    )

    ranked = rank_results([a, b, c])

    assert [item.content for item in ranked] == ["c", "a", "b"]


def test_retrieval_config_rejects_invalid_threshold_instead_of_clamping() -> None:
    with pytest.raises(ValueError):
        RetrievalConfig(min_final_score_threshold=1.5)

    with pytest.raises(ValueError):
        RetrievalConfig(min_final_score_threshold=-0.1)
