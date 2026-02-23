from backend.workflow.plan_compiler import compile_plan_to_workflow_graph


def test_compile_plan_to_workflow_graph_returns_expected_pipeline() -> None:
    graph = compile_plan_to_workflow_graph("chat")

    assert graph.nodes == ("router", "context_builder", "llm_worker", "validator")
    assert graph.entry == "router"
    assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
        ("router", "context_builder"),
        ("context_builder", "llm_worker"),
        ("llm_worker", "validator"),
    ]
