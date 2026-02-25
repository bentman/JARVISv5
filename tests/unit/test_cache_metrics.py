"""Unit tests for in-memory cache metrics collector (M6.3)."""
from __future__ import annotations

from backend.cache.metrics import CacheMetrics, get_metrics


def test_hit_miss_increments_and_category_counts() -> None:
    metrics = CacheMetrics()

    metrics.record_hit("context")
    metrics.record_hit("  ")  # normalize to general
    metrics.record_miss("context")
    metrics.record_miss("")  # normalize to general

    assert metrics.hits == 2
    assert metrics.misses == 2
    assert metrics.category_hits == {"context": 1, "general": 1}
    assert metrics.category_misses == {"context": 1, "general": 1}


def test_hit_rate_and_category_hit_rate_edge_cases() -> None:
    metrics = CacheMetrics()

    assert metrics.hit_rate() == 0.0
    assert metrics.category_hit_rate("missing") == 0.0

    metrics.record_hit("context")
    metrics.record_miss("context")
    metrics.record_hit("context")

    assert metrics.hit_rate() == 2 / 3
    assert metrics.category_hit_rate("context") == 2 / 3
    assert metrics.category_hit_rate("  context  ") == 2 / 3


def test_summary_stable_keys_and_formatted_percentages() -> None:
    metrics = CacheMetrics()
    metrics.record_hit("beta")
    metrics.record_miss("alpha")
    metrics.record_set()
    metrics.record_delete()
    metrics.record_error()

    summary = metrics.summary()

    assert set(summary.keys()) == {
        "total_requests",
        "hits",
        "misses",
        "hit_rate",
        "hit_rate_pct",
        "sets",
        "deletes",
        "errors",
        "categories",
    }
    assert summary["total_requests"] == 2
    assert summary["hit_rate"] == 0.5
    assert summary["hit_rate_pct"] == "50.00%"

    categories = summary["categories"]
    assert list(categories.keys()) == ["alpha", "beta"]  # sorted deterministic order
    assert categories["alpha"]["hit_rate"] == 0.0
    assert categories["alpha"]["hit_rate_pct"] == "0.00%"
    assert categories["beta"]["hit_rate"] == 1.0
    assert categories["beta"]["hit_rate_pct"] == "100.00%"


def test_reset_clears_all_state_deterministically() -> None:
    metrics = CacheMetrics()
    metrics.record_hit("context")
    metrics.record_miss("tool")
    metrics.record_set()
    metrics.record_delete()
    metrics.record_error()

    metrics.reset()

    assert metrics.hits == 0
    assert metrics.misses == 0
    assert metrics.sets == 0
    assert metrics.deletes == 0
    assert metrics.errors == 0
    assert metrics.category_hits == {}
    assert metrics.category_misses == {}
    assert metrics.summary()["hit_rate"] == 0.0
    assert metrics.summary()["hit_rate_pct"] == "0.00%"


def test_get_metrics_returns_global_singleton() -> None:
    first = get_metrics()
    second = get_metrics()
    assert first is second
