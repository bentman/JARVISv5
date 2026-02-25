"""In-memory cache metrics collector (M6.3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _normalize_category(category: str) -> str:
    normalized = str(category).strip()
    return normalized or "general"


@dataclass
class CacheMetrics:
    """Cache performance metrics with per-category breakdowns."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0

    category_hits: dict[str, int] = field(default_factory=dict)
    category_misses: dict[str, int] = field(default_factory=dict)

    def record_hit(self, category: str = "general") -> None:
        category_name = _normalize_category(category)
        self.hits += 1
        self.category_hits[category_name] = self.category_hits.get(category_name, 0) + 1

    def record_miss(self, category: str = "general") -> None:
        category_name = _normalize_category(category)
        self.misses += 1
        self.category_misses[category_name] = self.category_misses.get(category_name, 0) + 1

    def record_set(self) -> None:
        self.sets += 1

    def record_delete(self) -> None:
        self.deletes += 1

    def record_error(self) -> None:
        self.errors += 1

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def category_hit_rate(self, category: str) -> float:
        category_name = _normalize_category(category)
        hits = self.category_hits.get(category_name, 0)
        misses = self.category_misses.get(category_name, 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total

    def summary(self) -> dict[str, Any]:
        categories = sorted(set(self.category_hits.keys()) | set(self.category_misses.keys()))
        overall_rate = self.hit_rate()

        return {
            "total_requests": self.hits + self.misses,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": overall_rate,
            "hit_rate_pct": f"{overall_rate:.2%}",
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "categories": {
                category: {
                    "hits": self.category_hits.get(category, 0),
                    "misses": self.category_misses.get(category, 0),
                    "hit_rate": self.category_hit_rate(category),
                    "hit_rate_pct": f"{self.category_hit_rate(category):.2%}",
                }
                for category in categories
            },
        }

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.category_hits.clear()
        self.category_misses.clear()


_global_metrics = CacheMetrics()


def get_metrics() -> CacheMetrics:
    """Return global cache metrics instance."""
    return _global_metrics
