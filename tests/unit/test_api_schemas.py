from backend.api.schemas import (
    BudgetPeriod,
    BudgetResponse,
    CacheHealth,
    DetailedHealthResponse,
    HardwareHealth,
    ModelHealth,
    SettingsResponse,
    WorkflowGraph,
    WorkflowGraphEdge,
    WorkflowNodeEvent,
    WorkflowTelemetryResponse,
    SettingsUpdateRequest,
)
import pytest


def test_workflow_and_settings_schema_instantiation_and_dump() -> None:
    workflow = WorkflowTelemetryResponse(
        task_id="task-123",
        workflow_graph=WorkflowGraph(
            nodes=["router", "llm_worker"],
            edges=[WorkflowGraphEdge(from_node="router", to_node="llm_worker")],
            entry="router",
        ),
        workflow_execution_order=["router", "llm_worker"],
        node_events=[
            WorkflowNodeEvent(
                node_id="router",
                node_type="RouterNode",
                controller_state="PLAN",
                event_type="node_end",
                success=True,
                elapsed_ns=1000,
                start_offset_ns=10,
            )
        ],
    )

    settings = SettingsResponse(
        app_name="JARVISv5",
        debug=True,
        hardware_profile="Medium",
        log_level="INFO",
        model_path="models/",
        data_path="data/",
        backend_port=8000,
        default_search_provider="duckduckgo",
        cache_enabled=True,
        allow_model_escalation=True,
        escalation_provider="openai",
        escalation_budget_usd=2.5,
        escalation_configured_providers=["anthropic", "openai"],
    )

    workflow_dump = workflow.model_dump()
    settings_dump = settings.model_dump()

    assert workflow_dump["task_id"] == "task-123"
    assert "workflow_graph" in workflow_dump
    assert "workflow_execution_order" in workflow_dump
    assert "node_events" in workflow_dump

    assert settings_dump["app_name"] == "JARVISv5"
    assert settings_dump["backend_port"] == 8000
    assert "hardware_profile" in settings_dump
    assert "cache_enabled" in settings_dump
    assert settings_dump["allow_model_escalation"] is True
    assert settings_dump["escalation_provider"] == "openai"
    assert settings_dump["escalation_budget_usd"] == 2.5
    assert settings_dump["escalation_configured_providers"] == ["anthropic", "openai"]


def test_budget_and_detailed_health_schema_instantiation_and_dump() -> None:
    budget = BudgetResponse(
        daily=BudgetPeriod(limit_usd=5.0, spent_usd=1.25, remaining_usd=3.75),
        monthly=BudgetPeriod(limit_usd=50.0, spent_usd=12.5, remaining_usd=37.5),
    )

    health = DetailedHealthResponse(
        status="ok",
        service="JARVISv5-backend",
        hardware=HardwareHealth(profile="medium", type="CPU_ONLY", cpu_count=8, memory_gb=31.9),
        model=ModelHealth(selected="test-mini", profile="medium", role="chat"),
        cache=CacheHealth(enabled=True, connected=False),
    )

    budget_dump = budget.model_dump()
    health_dump = health.model_dump()

    assert "daily" in budget_dump
    assert "monthly" in budget_dump
    assert budget_dump["daily"]["spent_usd"] == 1.25

    assert health_dump["status"] == "ok"
    assert health_dump["service"] == "JARVISv5-backend"
    assert "hardware" in health_dump
    assert "model" in health_dump
    assert "cache" in health_dump


def test_settings_update_request_accepts_valid_escalation_fields() -> None:
    req = SettingsUpdateRequest(
        allow_model_escalation=True,
        escalation_provider=" OPENAI ",
    )

    assert req.allow_model_escalation is True
    assert req.escalation_provider == "openai"


def test_settings_update_request_rejects_escalation_budget_field() -> None:
    with pytest.raises(ValueError):
        SettingsUpdateRequest(escalation_budget_usd=3.0)


def test_settings_update_request_rejects_invalid_escalation_provider() -> None:
    with pytest.raises(ValueError):
        SettingsUpdateRequest(escalation_provider="unsupported")
