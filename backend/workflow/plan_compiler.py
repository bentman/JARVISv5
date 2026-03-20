from __future__ import annotations

from typing import Any

from backend.workflow.dag_executor import WorkflowEdge, WorkflowGraph


MAX_SUBTASKS = 3
PLANNING_MIN_INPUT_CHARS = 80
SUPPORTED_INTENTS: frozenset[str] = frozenset(
    {"chat", "code", "research", "planning", "writing"}
)


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


def build_constrained_plan(user_input: str, intent: str | None = "") -> dict[str, Any]:
    normalized_input = _normalize_user_input(user_input)
    decomposed = _decompose_user_input(normalized_input)
    normalized_intent = str(intent).strip().lower() if intent is not None else ""
    planning_intent_forced = normalized_intent == "planning"
    heuristic_triggered = (
        len(normalized_input) >= PLANNING_MIN_INPUT_CHARS and len(decomposed) >= 2
    )
    planning_triggered = (
        planning_intent_forced
        or heuristic_triggered
    )

    if planning_triggered:
        subtasks = decomposed[:MAX_SUBTASKS] if decomposed else [normalized_input]
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
    base_graph = WorkflowGraph(
        nodes=("router", "context_builder", "llm_worker", "validator"),
        edges=(
            WorkflowEdge("router", "context_builder"),
            WorkflowEdge("context_builder", "llm_worker"),
            WorkflowEdge("llm_worker", "validator"),
        ),
        entry="router",
    )

    intent = str(plan_artifact).strip().lower() if plan_artifact is not None else ""

    if intent == "chat":
        return base_graph
    if intent == "code":
        return base_graph
    if intent == "research":
        return base_graph
    if intent == "planning":
        return base_graph
    if intent == "writing":
        return base_graph

    return base_graph
