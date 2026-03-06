from __future__ import annotations

from typing import Any

from backend.workflow.dag_executor import WorkflowEdge, WorkflowGraph


MAX_SUBTASKS = 3
PLANNING_MIN_INPUT_CHARS = 80


def _normalize_user_input(user_input: str) -> str:
    return " ".join(str(user_input).strip().split())


def _decompose_user_input(user_input: str) -> list[str]:
    segments = [_normalize_user_input(user_input)]
    for delimiter in ("\n", ";", ".", " then ", " next "):
        next_segments: list[str] = []
        for segment in segments:
            next_segments.extend(segment.split(delimiter))
        segments = next_segments

    normalized = [segment.strip() for segment in segments if segment.strip()]
    return normalized


def build_constrained_plan(user_input: str) -> dict[str, Any]:
    normalized_input = _normalize_user_input(user_input)
    decomposed = _decompose_user_input(normalized_input)
    planning_triggered = (
        len(normalized_input) >= PLANNING_MIN_INPUT_CHARS and len(decomposed) >= 2
    )

    if planning_triggered:
        subtasks = decomposed[:MAX_SUBTASKS]
        return {
            "mode": "planned",
            "subtasks": subtasks,
            "max_subtasks": MAX_SUBTASKS,
        }

    return {
        "mode": "linear",
        "subtasks": [normalized_input] if normalized_input else [],
        "max_subtasks": MAX_SUBTASKS,
    }


def compile_plan_to_workflow_graph(plan_artifact: str | None) -> WorkflowGraph:
    _ = plan_artifact
    return WorkflowGraph(
        nodes=("router", "context_builder", "llm_worker", "validator"),
        edges=(
            WorkflowEdge("router", "context_builder"),
            WorkflowEdge("context_builder", "llm_worker"),
            WorkflowEdge("llm_worker", "validator"),
        ),
        entry="router",
    )
