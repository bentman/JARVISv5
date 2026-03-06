from backend.workflow.plan_compiler import build_constrained_plan, compile_plan_to_workflow_graph


def test_compile_plan_to_workflow_graph_returns_expected_pipeline() -> None:
    graph = compile_plan_to_workflow_graph("chat")

    assert graph.nodes == ("router", "context_builder", "llm_worker", "validator")
    assert graph.entry == "router"
    assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
        ("router", "context_builder"),
        ("context_builder", "llm_worker"),
        ("llm_worker", "validator"),
    ]


def test_build_constrained_plan_linear_for_short_input() -> None:
    plan = build_constrained_plan("short prompt")

    assert plan["mode"] == "linear"
    assert plan["subtasks"] == ["short prompt"]
    assert plan["max_subtasks"] == 3


def test_build_constrained_plan_planned_for_complex_input_with_stable_order() -> None:
    text = (
        "This is a long and complex prompt that should trigger constrained planning because "
        "it exceeds the threshold and includes multiple tasks; first gather data; then summarize "
        "findings. next provide recommendations."
    )

    plan = build_constrained_plan(text)

    assert plan["mode"] == "planned"
    assert plan["subtasks"] == [
        "This is a long and complex prompt that should trigger constrained planning because it exceeds the threshold and includes multiple tasks",
        "first gather data",
        "summarize findings",
    ]
    assert plan["max_subtasks"] == 3


def test_build_constrained_plan_caps_fanout_to_max_subtasks() -> None:
    text = (
        "This prompt is intentionally long enough to trigger planning and produce many segments; "
        "step one; step two; step three; step four; step five."
    )

    plan = build_constrained_plan(text)

    assert plan["mode"] == "planned"
    assert len(plan["subtasks"]) == 3
