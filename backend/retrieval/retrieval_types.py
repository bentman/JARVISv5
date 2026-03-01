from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any


def _clamp01(value: float) -> float:
    value_f = float(value)
    if value_f < 0.0:
        return 0.0
    if value_f > 1.0:
        return 1.0
    return value_f


class SourceType(str, Enum):
    WORKING_STATE = "working_state"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"


@dataclass
class RetrievalConfig:
    relevance_weight: float = 0.7
    recency_weight: float = 0.3
    max_results: int = 10
    min_final_score_threshold: float = 0.0
    semantic_recency_default: float = 0.5
    episodic_recency_default: float = 0.5
    episodic_decision_relevance: float = 0.65
    episodic_toolcall_relevance: float = 0.6
    working_state_match_relevance: float = 0.8
    working_state_nomatch_relevance: float = 0.4
    ws_decay_tau: float = 3.0
    time_decay_tau_hours: float = 24.0
    working_state_window: int = 50

    def __post_init__(self) -> None:
        self.relevance_weight = float(self.relevance_weight)
        self.recency_weight = float(self.recency_weight)

        if not isfinite(self.relevance_weight) or self.relevance_weight < 0.0:
            raise ValueError("relevance_weight must be a finite number >= 0")
        if not isfinite(self.recency_weight) or self.recency_weight < 0.0:
            raise ValueError("recency_weight must be a finite number >= 0")

        weight_sum = self.relevance_weight + self.recency_weight
        if weight_sum <= 0.0:
            raise ValueError("relevance_weight + recency_weight must be > 0")

        self.max_results = int(self.max_results)
        if self.max_results < 1:
            raise ValueError("max_results must be >= 1")

        self.min_final_score_threshold = float(self.min_final_score_threshold)
        if not 0.0 <= self.min_final_score_threshold <= 1.0:
            raise ValueError("min_final_score_threshold must be within [0.0, 1.0]")

        for field_name in (
            "semantic_recency_default",
            "episodic_recency_default",
            "episodic_decision_relevance",
            "episodic_toolcall_relevance",
            "working_state_match_relevance",
            "working_state_nomatch_relevance",
        ):
            field_value = float(getattr(self, field_name))
            setattr(self, field_name, field_value)
            if not 0.0 <= field_value <= 1.0:
                raise ValueError(f"{field_name} must be within [0.0, 1.0]")

        self.ws_decay_tau = float(self.ws_decay_tau)
        if not isfinite(self.ws_decay_tau) or self.ws_decay_tau <= 0.0:
            raise ValueError("ws_decay_tau must be a finite number > 0")

        self.time_decay_tau_hours = float(self.time_decay_tau_hours)
        if not isfinite(self.time_decay_tau_hours) or self.time_decay_tau_hours <= 0.0:
            raise ValueError("time_decay_tau_hours must be a finite number > 0")

        self.working_state_window = int(self.working_state_window)
        if self.working_state_window < 1:
            raise ValueError("working_state_window must be >= 1")


def compute_final_score(
    relevance_score: float,
    recency_score: float,
    config: RetrievalConfig,
) -> float:
    relevance = _clamp01(relevance_score)
    recency = _clamp01(recency_score)
    weighted = (relevance * config.relevance_weight) + (recency * config.recency_weight)
    normalized = weighted / (config.relevance_weight + config.recency_weight)
    return _clamp01(normalized)


@dataclass
class RetrievalResult:
    source: SourceType
    content: str
    relevance_score: float
    recency_score: float
    task_id: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    final_score: float = field(init=False)

    def __post_init__(self) -> None:
        self.relevance_score = _clamp01(self.relevance_score)
        self.recency_score = _clamp01(self.recency_score)
        self.final_score = compute_final_score(
            self.relevance_score,
            self.recency_score,
            RetrievalConfig(),
        )

    @classmethod
    def from_scores(
        cls,
        *,
        source: SourceType,
        content: str,
        relevance_score: float,
        recency_score: float,
        config: RetrievalConfig,
        task_id: str | None = None,
        timestamp: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        result = cls(
            source=source,
            content=content,
            relevance_score=relevance_score,
            recency_score=recency_score,
            task_id=task_id,
            timestamp=timestamp,
            metadata={} if metadata is None else dict(metadata),
        )
        result.final_score = compute_final_score(
            result.relevance_score,
            result.recency_score,
            config,
        )
        return result


def rank_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    return sorted(results, key=lambda item: item.final_score, reverse=True)
