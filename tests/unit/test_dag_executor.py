import pytest

from backend.workflow.dag_executor import DAGExecutor, WorkflowEdge, WorkflowGraph, WorkflowGraphError


class _Node:
    def __init__(self, name: str) -> None:
        self.name = name

    def execute(self, context: dict) -> dict:
        trail = list(context.get("trail", []))
        trail.append(self.name)
        context["trail"] = trail
        return context


def test_dag_executor_topological_order_and_execute() -> None:
    graph = WorkflowGraph(
        nodes=("router", "context_builder", "llm_worker", "validator"),
        edges=(
            WorkflowEdge("router", "context_builder"),
            WorkflowEdge("context_builder", "llm_worker"),
            WorkflowEdge("llm_worker", "validator"),
        ),
        entry="router",
    )
    registry = {
        "router": _Node("router"),
        "context_builder": _Node("context_builder"),
        "llm_worker": _Node("llm_worker"),
        "validator": _Node("validator"),
    }
    executor = DAGExecutor()

    order = executor.resolve_execution_order(graph, registry)
    assert order == ["router", "context_builder", "llm_worker", "validator"]

    result = executor.execute(graph, registry, {"trail": []})
    assert result["trail"] == order


def test_dag_executor_fails_on_missing_node_dependency() -> None:
    graph = WorkflowGraph(
        nodes=("router", "context_builder"),
        edges=(WorkflowEdge("router", "context_builder"),),
        entry="router",
    )
    registry = {
        "router": _Node("router"),
    }

    with pytest.raises(WorkflowGraphError, match="missing node implementations"):
        DAGExecutor().resolve_execution_order(graph, registry)


def test_dag_executor_fails_closed_on_cycle() -> None:
    graph = WorkflowGraph(
        nodes=("router", "context_builder", "llm_worker"),
        edges=(
            WorkflowEdge("router", "context_builder"),
            WorkflowEdge("context_builder", "llm_worker"),
            WorkflowEdge("llm_worker", "router"),
        ),
        entry="router",
    )
    registry = {
        "router": _Node("router"),
        "context_builder": _Node("context_builder"),
        "llm_worker": _Node("llm_worker"),
    }

    with pytest.raises(WorkflowGraphError, match="contains a cycle"):
        DAGExecutor().resolve_execution_order(graph, registry)
