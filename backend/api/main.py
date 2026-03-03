import os
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from backend.api.schemas import (
    BudgetPeriod,
    BudgetResponse,
    CacheHealth,
    DetailedHealthResponse,
    HardwareHealth,
    ModelHealth,
    SettingsResponse,
    WorkflowNodeEvent,
    WorkflowTelemetryResponse,
)
from backend.cache import redis_client as cache_redis_client
from backend.config.settings import Settings
from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models import hardware_profiler
from backend.models import model_registry
from backend.search import budget as search_budget


app = FastAPI(title="JARVISv5 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str | None = None
    user_input: str = Field(
        ...,
        validation_alias=AliasChoices("user_input", "input"),
    )


def _build_memory_manager(settings: Settings) -> MemoryManager:
    data_root = Path(settings.DATA_PATH)
    return MemoryManager(
        episodic_db_path=str(data_root / "episodic" / "trace.db"),
        working_base_path=str(data_root / "working_state"),
        working_archive_path=str(data_root / "archives"),
        semantic_db_path=str(data_root / "semantic" / "metadata.db"),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "JARVISv5-backend"}


@app.get("/health/ready")
def health_ready() -> dict[str, bool | str]:
    service_name = "JARVISv5-backend"
    try:
        settings = Settings()
        _build_memory_manager(settings)
        return {
            "ready": True,
            "service": service_name,
            "detail": "ready",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "service": service_name,
                "detail": "readiness_unavailable",
            },
        ) from exc


@app.get("/health/detailed", response_model=DetailedHealthResponse)
def detailed_health() -> DetailedHealthResponse:
    try:
        service_name = "JARVISv5-backend"

        hardware: HardwareHealth | None = None
        hardware_type_for_model = "CPU_ONLY"
        try:
            hardware_service = hardware_profiler.HardwareService()
            system_info = hardware_service.get_system_info()
            detected_hardware_type = hardware_service.detect_hardware_type()
            hardware_type_for_model = str(getattr(detected_hardware_type, "value", "CPU_ONLY"))

            hardware = HardwareHealth(
                profile=hardware_service.get_hardware_profile(),
                type=hardware_type_for_model,
                cpu_count=int(system_info.get("cpu_cores", 0) or 0),
                memory_gb=float(system_info.get("total_ram_gb", 0.0) or 0.0),
            )
        except Exception:
            hardware = None

        model: ModelHealth | None = None
        try:
            settings = Settings()
            registry = model_registry.ModelRegistry()
            selected = registry.select_model(
                profile=str(settings.HARDWARE_PROFILE),
                hardware=hardware_type_for_model,
                role="chat",
            )
            model = ModelHealth(
                selected=str(selected.get("id")) if isinstance(selected, dict) and selected.get("id") else None,
                profile=str(settings.HARDWARE_PROFILE),
                role="chat",
            )
        except Exception:
            model = None

        cache: CacheHealth | None = None
        try:
            cache_client = cache_redis_client.create_default_redis_client()
            cache_status = cache_client.health_check()
            cache = CacheHealth(
                enabled=bool(cache_status.get("enabled")),
                connected=bool(cache_status.get("connected")),
            )
        except Exception:
            cache = None

        degraded = False
        if hardware is None:
            degraded = True
        if model is None or model.selected is None:
            degraded = True
        if cache is None:
            degraded = True
        elif bool(cache.enabled) and not bool(cache.connected):
            degraded = True

        return DetailedHealthResponse(
            status="degraded" if degraded else "ok",
            service=service_name,
            hardware=hardware,
            model=model,
            cache=cache,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="health_details_unavailable") from exc


@app.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    try:
        settings = Settings()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="settings_unavailable") from exc

    return SettingsResponse(
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
        hardware_profile=settings.HARDWARE_PROFILE,
        log_level=settings.LOG_LEVEL,
        model_path=settings.MODEL_PATH,
        data_path=settings.DATA_PATH,
        backend_port=settings.BACKEND_PORT,
    )


@app.get("/budget", response_model=BudgetResponse)
def get_budget() -> BudgetResponse:
    try:
        daily_limit_usd = float(os.getenv("DAILY_BUDGET_USD", "0.0"))
        config = search_budget.SearchBudgetConfig(daily_limit_usd=daily_limit_usd)
        ledger = search_budget.SearchBudgetLedger()
        date_key = ledger.today_key()
        spent_usd = ledger.get_spent(date_key)
        remaining_usd = ledger.remaining_budget_usd(date_key, config.daily_limit_usd)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="budget_unavailable") from exc

    return BudgetResponse(
        daily=BudgetPeriod(
            limit_usd=float(config.daily_limit_usd),
            spent_usd=float(spent_usd),
            remaining_usd=float(remaining_usd),
        ),
        monthly=None,
    )


@app.post("/task")
def create_task(request: TaskRequest) -> dict[str, str]:
    settings = Settings()
    memory = _build_memory_manager(settings)

    if request.task_id is not None and memory.get_task_state(request.task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    service = ControllerService(memory_manager=memory)
    result = service.run(user_input=request.user_input, task_id=request.task_id)
    context = result.get("context", {})

    return {
        "task_id": str(result.get("task_id", "")),
        "final_state": str(result.get("final_state", "")),
        "llm_output": str(context.get("llm_output", "")),
    }


@app.get("/task/{task_id}")
def get_task(task_id: str) -> dict:
    settings = Settings()
    memory = _build_memory_manager(settings)
    task_state = memory.get_task_state(task_id)
    if task_state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_state


@app.get("/workflow/{task_id}", response_model=WorkflowTelemetryResponse)
def get_workflow_telemetry(task_id: str) -> WorkflowTelemetryResponse:
    settings = Settings()
    memory = _build_memory_manager(settings)

    task_state = memory.get_task_state(task_id)
    if task_state is None:
        raise HTTPException(status_code=404, detail="Task not found")

    workflow_graph = task_state.get("workflow_graph", {}) if isinstance(task_state, dict) else {}
    if not isinstance(workflow_graph, dict):
        workflow_graph = {}

    workflow_execution_order = (
        task_state.get("workflow_execution_order", []) if isinstance(task_state, dict) else []
    )
    if not isinstance(workflow_execution_order, list):
        workflow_execution_order = []

    node_events: list[WorkflowNodeEvent] = []
    decisions = memory.episodic.search_decisions(query="dag_node_event", task_id=task_id, limit=1000)
    ordered_decisions = sorted(
        decisions,
        key=lambda item: int(item.get("id", 0)) if isinstance(item, dict) else 0,
    )
    for decision in ordered_decisions:
        if not isinstance(decision, dict):
            continue
        if str(decision.get("action_type", "")) != "dag_node_event":
            continue

        content = decision.get("content", "")
        if not isinstance(content, str):
            continue

        try:
            payload = json.loads(content)
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        node_events.append(
            WorkflowNodeEvent(
                node_id=str(payload.get("node_id", "")),
                node_type=str(payload.get("node_type", "")),
                controller_state=str(payload.get("controller_state", "")),
                event_type=str(payload.get("event_type", "")),
                success=bool(payload.get("success", False)),
                task_id=str(payload.get("task_id")) if payload.get("task_id") is not None else None,
                elapsed_ns=int(payload.get("elapsed_ns")) if payload.get("elapsed_ns") is not None else None,
                start_offset_ns=(
                    int(payload.get("start_offset_ns"))
                    if payload.get("start_offset_ns") is not None
                    else None
                ),
                error=str(payload.get("error")) if payload.get("error") is not None else None,
            )
        )

    return WorkflowTelemetryResponse(
        task_id=task_id,
        workflow_graph=workflow_graph,
        workflow_execution_order=workflow_execution_order,
        node_events=node_events,
    )
