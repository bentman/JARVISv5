from backend.workflow.plan_compiler import (
    SUPPORTED_INTENTS,
    build_constrained_plan,
    compile_plan_to_workflow_graph,
)


def test_compile_plan_to_workflow_graph_returns_expected_pipeline() -> None:
    graph = compile_plan_to_workflow_graph("chat")

    assert graph.nodes == ("router", "context_builder", "llm_worker", "validator")
    assert graph.entry == "router"
    assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
        ("router", "context_builder"),
        ("context_builder", "llm_worker"),
        ("llm_worker", "validator"),
    ]


def test_supported_intents_constant_contains_expected_set() -> None:
    assert SUPPORTED_INTENTS == {"chat", "code", "research", "planning", "writing"}


def test_compile_plan_to_workflow_graph_returns_same_shape_for_all_supported_intents() -> None:
    expected = compile_plan_to_workflow_graph("chat")

    for intent in sorted(SUPPORTED_INTENTS):
        graph = compile_plan_to_workflow_graph(intent)
        assert graph.nodes == expected.nodes
        assert graph.entry == expected.entry
        assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
            (edge.from_node, edge.to_node) for edge in expected.edges
        ]


def test_compile_plan_to_workflow_graph_none_intent_is_deterministic_fallback() -> None:
    graph = compile_plan_to_workflow_graph(None)
    expected = compile_plan_to_workflow_graph("chat")

    assert graph.nodes == expected.nodes
    assert graph.entry == expected.entry
    assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
        (edge.from_node, edge.to_node) for edge in expected.edges
    ]


def test_compile_plan_to_workflow_graph_unsupported_intent_is_deterministic_fallback() -> None:
    graph = compile_plan_to_workflow_graph("unknown_intent")
    expected = compile_plan_to_workflow_graph("chat")

    assert graph.nodes == expected.nodes
    assert graph.entry == expected.entry
    assert [(edge.from_node, edge.to_node) for edge in graph.edges] == [
        (edge.from_node, edge.to_node) for edge in expected.edges
    ]


def test_build_constrained_plan_linear_for_short_input() -> None:
    plan = build_constrained_plan("short prompt", intent="planning")

    assert plan["mode"] == "planned"
    assert plan["subtasks"] == ["short prompt"]
    assert plan["max_subtasks"] == 3


def test_build_constrained_plan_planned_for_complex_input_with_stable_order() -> None:
    text = (
        "This is a long and complex prompt that should trigger constrained planning because "
        "it exceeds the threshold and includes multiple tasks; first gather data; then summarize "
        "findings. next provide recommendations."
    )

    plan = build_constrained_plan(text, intent="planning")

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

    plan = build_constrained_plan(text, intent="writing")

    assert plan["mode"] == "planned"
    assert len(plan["subtasks"]) == 3


def test_build_constrained_plan_chat_intent_uses_heuristic_when_decomposable() -> None:
    text = (
        "This is a long and complex prompt that should trigger constrained planning because "
        "it exceeds the threshold and includes multiple tasks; first gather data; then summarize "
        "findings. next provide recommendations."
    )

    plan = build_constrained_plan(text, intent="chat")

    assert plan["mode"] == "planned"
    assert len(plan["subtasks"]) == 3


def test_build_constrained_plan_code_intent_uses_heuristic_when_decomposable() -> None:
    text = (
        "This is a long and complex prompt that should trigger constrained planning because "
        "it exceeds the threshold and includes multiple tasks; first gather data; then summarize "
        "findings. next provide recommendations."
    )

    plan = build_constrained_plan(text, intent="code")

    assert plan["mode"] == "planned"


def test_build_constrained_plan_research_intent_uses_heuristic_when_decomposable() -> None:
    text = (
        "This is a long and complex prompt that should trigger constrained planning because "
        "it exceeds the threshold and includes multiple tasks; first gather data; then summarize "
        "findings. next provide recommendations."
    )

    plan = build_constrained_plan(text, intent="research")

    assert plan["mode"] == "planned"


def test_build_constrained_plan_unsupported_intent_is_deterministic_linear_fallback() -> None:
    text = "short prompt"

    plan = build_constrained_plan(text, intent="unsupported_intent")

    assert plan["mode"] == "linear"


def test_build_constrained_plan_none_intent_is_deterministic_linear_fallback() -> None:
    text = "short prompt"

    plan = build_constrained_plan(text, intent=None)

    assert plan["mode"] == "linear"
