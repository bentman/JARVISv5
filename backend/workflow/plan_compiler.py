from __future__ import annotations

from backend.workflow.dag_executor import WorkflowEdge, WorkflowGraph


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
