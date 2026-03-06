import json
import time
from email.parser import BytesParser
from email.policy import default as email_default_policy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from backend.api.schemas import (
    BudgetPeriod,
    BudgetResponse,
    CacheHealth,
    DetailedHealthResponse,
    HardwareHealth,
    ModelHealth,
    SettingsResponse,
    SettingsUpdateRequest,
    TaskFailureMetadata,
    TaskResponse,
    WorkflowNodeEvent,
    WorkflowTelemetryResponse,
)
from backend.cache import redis_client as cache_redis_client
from backend.config.settings import (
    Settings,
    get_safe_config_projection,
    persist_settings_updates,
    settings_update_restart_semantics,
)
from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models import hardware_profiler
from backend.models import model_registry
from backend.search import budget as search_budget
from backend.tools.file_tools import extract_upload_text


app = FastAPI(title="JARVISv5 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Detailed health cache is intentionally in-process (module memory):
# - Scope: per worker/process only (not shared across workers/pods/instances)
# - TTL: 30 seconds
# - Purpose: reduce expensive diagnostics for lower-frequency detailed polling
_DETAILED_HEALTH_CACHE_TTL_SECONDS = 30.0
_detailed_health_cache: DetailedHealthResponse | None = None
_detailed_health_cache_timestamp = 0.0
_SETTINGS_ENV_PATH = Path(".env")


def _monotonic_now() -> float:
    return time.monotonic()


class TaskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    task_id: str | None = None
    user_input: str = Field(
        ...,
        validation_alias=AliasChoices("user_input", "input"),
    )


class BudgetUpdateRequest(BaseModel):
    daily_limit_usd: float | None = Field(default=None, ge=0.0)
    monthly_limit_usd: float | None = Field(default=None, ge=0.0)


def _format_sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _build_tool_preview_payload(tool_result: Any) -> dict[str, Any] | None:
    if not isinstance(tool_result, dict):
        return None

    attempted_raw = tool_result.get("attempted_providers", [])
    attempted = attempted_raw if isinstance(attempted_raw, list) else []

    items_raw = tool_result.get("items", [])
    items = items_raw if isinstance(items_raw, list) else []

    tool_name = tool_result.get("tool_name")
    code = tool_result.get("code")
    reason = tool_result.get("reason")

    return {
        "tool_name": str(tool_name) if tool_name is not None else None,
        "code": str(code) if code is not None else None,
        "reason": str(reason) if reason is not None else None,
        "attempted_providers": [str(name) for name in attempted],
        "items": items,
    }


def _compose_user_input_with_attachment(*, user_input: str, filename: str, attachment_text: str) -> str:
    return (
        f"{user_input}\n\n"
        "[ATTACHMENT_CONTEXT_BEGIN]\n"
        f"filename={filename}\n"
        f"{attachment_text}\n"
        "[ATTACHMENT_CONTEXT_END]"
    )


def _parse_multipart_task_upload(
    *,
    content_type: str,
    body: bytes,
) -> tuple[bool, dict[str, Any]]:
    if not str(content_type).lower().startswith("multipart/form-data"):
        return False, {"code": "invalid_content_type", "reason": "multipart_form_data_required"}

    pseudo_message = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("utf-8") + body

    try:
        message = BytesParser(policy=email_default_policy).parsebytes(pseudo_message)
    except Exception as exc:
        return False, {"code": "invalid_multipart_payload", "reason": str(exc)}

    if not message.is_multipart():
        return False, {"code": "invalid_multipart_payload", "reason": "not_multipart"}

    fields: dict[str, str] = {}
    upload_file: dict[str, Any] | None = None

    for part in message.iter_parts():
        disposition = str(part.get("Content-Disposition", ""))
        if "form-data" not in disposition.lower():
            continue
        field_name = part.get_param("name", header="content-disposition")
        if not field_name:
            continue

        filename = part.get_param("filename", header="content-disposition")
        payload_raw: Any = part.get_payload(decode=True)
        payload = payload_raw if isinstance(payload_raw, bytes) else b""

        if filename and upload_file is None:
            upload_file = {
                "filename": str(filename),
                "mime_type": str(part.get_content_type() or "application/octet-stream"),
                "content": payload,
            }
            continue

        fields[str(field_name)] = payload.decode("utf-8", errors="replace")

    return True, {
        "user_input": str(fields.get("user_input", "")),
        "task_id": str(fields.get("task_id")) if fields.get("task_id") else None,
        "file": upload_file,
    }


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
    global _detailed_health_cache, _detailed_health_cache_timestamp

    now = _monotonic_now()
    if (
        _detailed_health_cache is not None
        and (now - _detailed_health_cache_timestamp) < _DETAILED_HEALTH_CACHE_TTL_SECONDS
    ):
        return _detailed_health_cache

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

        result = DetailedHealthResponse(
            status="degraded" if degraded else "ok",
            service=service_name,
            hardware=hardware,
            model=model,
            cache=cache,
        )
        _detailed_health_cache = result
        _detailed_health_cache_timestamp = now
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail="health_details_unavailable") from exc


@app.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    try:
        settings = Settings()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="settings_unavailable") from exc

    projection = get_safe_config_projection(settings)
    return SettingsResponse(
        app_name=projection["app_name"],
        debug=projection["debug"],
        hardware_profile=projection["hardware_profile"],
        log_level=projection["log_level"],
        model_path=projection["model_path"],
        data_path=projection["data_path"],
        backend_port=projection["backend_port"],
        redact_pii_queries=projection["redact_pii_queries"],
        redact_pii_results=projection["redact_pii_results"],
        allow_external_search=projection["allow_external_search"],
        default_search_provider=projection["default_search_provider"],
        cache_enabled=projection["cache_enabled"],
    )


@app.post("/settings", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest, response: Response) -> SettingsResponse:
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="no_settings_updates_provided")

    try:
        persist_settings_updates(updates=updates, env_path=_SETTINGS_ENV_PATH)
        semantics = settings_update_restart_semantics(set(updates.keys()))
        settings = Settings()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="settings_update_unavailable") from exc

    response.headers["X-Settings-Restart-Required"] = (
        "true" if bool(semantics.get("restart_required", False)) else "false"
    )
    restart_required_fields = semantics.get("restart_required_fields", [])
    hot_applied_fields = semantics.get("hot_applied_fields", [])
    restart_required_list = (
        [str(item) for item in restart_required_fields]
        if isinstance(restart_required_fields, list)
        else []
    )
    hot_applied_list = (
        [str(item) for item in hot_applied_fields]
        if isinstance(hot_applied_fields, list)
        else []
    )
    response.headers["X-Settings-Restart-Required-Fields"] = ",".join(restart_required_list)
    response.headers["X-Settings-Hot-Applied-Fields"] = ",".join(hot_applied_list)

    projection = get_safe_config_projection(settings)
    for field_name, value in updates.items():
        if field_name in projection:
            projection[field_name] = value

    return SettingsResponse(
        app_name=projection["app_name"],
        debug=projection["debug"],
        hardware_profile=projection["hardware_profile"],
        log_level=projection["log_level"],
        model_path=projection["model_path"],
        data_path=projection["data_path"],
        backend_port=projection["backend_port"],
        redact_pii_queries=projection["redact_pii_queries"],
        redact_pii_results=projection["redact_pii_results"],
        allow_external_search=projection["allow_external_search"],
        default_search_provider=projection["default_search_provider"],
        cache_enabled=projection["cache_enabled"],
    )


@app.get("/budget", response_model=BudgetResponse)
def get_budget() -> BudgetResponse:
    try:
        settings = Settings()
        config = search_budget.SearchBudgetConfig(daily_limit_usd=float(settings.DAILY_BUDGET_USD))
        ledger = search_budget.SearchBudgetLedger()
        date_key = ledger.today_key()
        spent_usd = ledger.get_spent(date_key)
        remaining_usd = ledger.remaining_budget_usd(date_key, config.daily_limit_usd)
        monthly_summary = ledger.get_monthly_summary(
            monthly_limit_usd=float(settings.MONTHLY_BUDGET_USD),
            end_date_key=date_key,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="budget_unavailable") from exc

    return BudgetResponse(
        daily=BudgetPeriod(
            limit_usd=float(config.daily_limit_usd),
            spent_usd=float(spent_usd),
            remaining_usd=float(remaining_usd),
        ),
        monthly=BudgetPeriod(
            limit_usd=float(monthly_summary["limit_usd"]),
            spent_usd=float(monthly_summary["spent_usd"]),
            remaining_usd=float(monthly_summary["remaining_usd"]),
        ),
    )


@app.post("/budget", response_model=BudgetResponse)
def update_budget(request: BudgetUpdateRequest) -> BudgetResponse:
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="no_budget_updates_provided")

    try:
        search_budget.persist_budget_limit_updates(
            updates=updates,
            env_path=_SETTINGS_ENV_PATH,
        )
        settings = Settings()
        daily_limit_usd = float(updates.get("daily_limit_usd", settings.DAILY_BUDGET_USD))
        monthly_limit_usd = float(updates.get("monthly_limit_usd", settings.MONTHLY_BUDGET_USD))
        config = search_budget.SearchBudgetConfig(daily_limit_usd=daily_limit_usd)
        ledger = search_budget.SearchBudgetLedger()
        date_key = ledger.today_key()
        spent_usd = ledger.get_spent(date_key)
        remaining_usd = ledger.remaining_budget_usd(date_key, config.daily_limit_usd)
        monthly_summary = ledger.get_monthly_summary(
            monthly_limit_usd=monthly_limit_usd,
            end_date_key=date_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="budget_update_unavailable") from exc

    return BudgetResponse(
        daily=BudgetPeriod(
            limit_usd=float(config.daily_limit_usd),
            spent_usd=float(spent_usd),
            remaining_usd=float(remaining_usd),
        ),
        monthly=BudgetPeriod(
            limit_usd=float(monthly_summary["limit_usd"]),
            spent_usd=float(monthly_summary["spent_usd"]),
            remaining_usd=float(monthly_summary["remaining_usd"]),
        ),
    )


@app.post("/task", response_model=TaskResponse)
def create_task(request: TaskRequest) -> TaskResponse:
    settings = Settings()
    memory = _build_memory_manager(settings)

    if request.task_id is not None and memory.get_task_state(request.task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    service = ControllerService(
        memory_manager=memory,
        generation_seed=settings.GENERATION_SEED,
    )
    result = service.run(user_input=request.user_input, task_id=request.task_id)
    context = result.get("context", {})
    tool_result = context.get("tool_result") if isinstance(context, dict) else None
    tool_ok = bool(context.get("tool_ok", True)) if isinstance(context, dict) else True

    failure: TaskFailureMetadata | None = None
    if not tool_ok and isinstance(tool_result, dict):
        attempted_raw = tool_result.get("attempted_providers", [])
        attempted = attempted_raw if isinstance(attempted_raw, list) else []
        failure = TaskFailureMetadata(
            reason=str(tool_result.get("reason")) if tool_result.get("reason") is not None else None,
            attempted_providers=[str(name) for name in attempted],
            code=str(tool_result.get("code")) if tool_result.get("code") is not None else None,
        )

    return TaskResponse(
        task_id=str(result.get("task_id", "")),
        final_state=str(result.get("final_state", "")),
        llm_output=str(context.get("llm_output", "")),
        failure=failure,
    )


@app.post("/task/upload")
async def create_task_upload(request: Request) -> dict[str, Any]:
    content_type = str(request.headers.get("content-type", ""))
    body = await request.body()
    ok_payload, parsed = _parse_multipart_task_upload(content_type=content_type, body=body)
    if not ok_payload:
        raise HTTPException(status_code=400, detail=parsed)

    user_input = str(parsed.get("user_input", ""))
    task_id_raw = parsed.get("task_id")
    task_id = str(task_id_raw) if task_id_raw is not None else None
    uploaded_file = parsed.get("file") if isinstance(parsed, dict) else None
    if not user_input.strip():
        raise HTTPException(status_code=422, detail={"code": "missing_user_input"})

    settings = Settings()
    memory = _build_memory_manager(settings)

    if task_id is not None and memory.get_task_state(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    effective_user_input = str(user_input)
    attachment_payload: dict[str, Any] | None = None

    if isinstance(uploaded_file, dict):
        raw_bytes = uploaded_file.get("content", b"")
        if not isinstance(raw_bytes, bytes):
            raw_bytes = b""
        ok, extracted = extract_upload_text(
            filename=str(uploaded_file.get("filename", "")),
            mime_type=str(uploaded_file.get("mime_type", "application/octet-stream")),
            raw_bytes=raw_bytes,
        )
        if not ok:
            code = str(extracted.get("code", "file_extraction_failed"))
            if code == "unsupported_file_type":
                raise HTTPException(status_code=415, detail=extracted)
            raise HTTPException(status_code=422, detail=extracted)

        effective_user_input = _compose_user_input_with_attachment(
            user_input=str(user_input),
            filename=str(extracted.get("filename", "attachment")),
            attachment_text=str(extracted.get("text", "")),
        )
        extracted_text_length_raw = extracted.get("extracted_text_length", 0)
        extracted_text_length = (
            int(extracted_text_length_raw)
            if isinstance(extracted_text_length_raw, (int, float, str))
            else 0
        )
        truncated_raw = extracted.get("truncated", False)
        truncated = bool(truncated_raw) if isinstance(truncated_raw, (bool, int)) else False
        attachment_payload = {
            "filename": str(extracted.get("filename", "")),
            "mime_type": str(extracted.get("mime_type", "application/octet-stream")),
            "extracted_text_length": extracted_text_length,
            "size_bytes": int(len(raw_bytes)),
            "truncated": truncated,
        }

    service = ControllerService(
        memory_manager=memory,
        generation_seed=settings.GENERATION_SEED,
    )
    result = service.run(user_input=effective_user_input, task_id=task_id)
    context = result.get("context", {})
    tool_result = context.get("tool_result") if isinstance(context, dict) else None
    tool_ok = bool(context.get("tool_ok", True)) if isinstance(context, dict) else True

    failure_data: dict[str, Any] | None = None
    if not tool_ok and isinstance(tool_result, dict):
        attempted_raw = tool_result.get("attempted_providers", [])
        attempted = attempted_raw if isinstance(attempted_raw, list) else []
        failure_data = {
            "reason": str(tool_result.get("reason")) if tool_result.get("reason") is not None else None,
            "attempted_providers": [str(name) for name in attempted],
            "code": str(tool_result.get("code")) if tool_result.get("code") is not None else None,
        }

    return {
        "task_id": str(result.get("task_id", "")),
        "final_state": str(result.get("final_state", "")),
        "llm_output": str(context.get("llm_output", "")) if isinstance(context, dict) else "",
        "failure": failure_data,
        "attachment": attachment_payload,
    }


@app.post("/task/stream")
def create_task_stream(request: TaskRequest) -> StreamingResponse:
    settings = Settings()
    memory = _build_memory_manager(settings)

    if request.task_id is not None and memory.get_task_state(request.task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")

    service = ControllerService(
        memory_manager=memory,
        generation_seed=settings.GENERATION_SEED,
    )

    def _event_stream() -> Any:
        try:
            result = service.run(user_input=request.user_input, task_id=request.task_id)
            context = result.get("context", {})
            tool_result = context.get("tool_result") if isinstance(context, dict) else None
            tool_ok = bool(context.get("tool_ok", True)) if isinstance(context, dict) else True
            tool_preview = _build_tool_preview_payload(tool_result)

            failure_data: dict[str, Any] | None = None
            if not tool_ok and isinstance(tool_result, dict):
                attempted_raw = tool_result.get("attempted_providers", [])
                attempted = attempted_raw if isinstance(attempted_raw, list) else []
                failure_data = {
                    "reason": (
                        str(tool_result.get("reason"))
                        if tool_result.get("reason") is not None
                        else None
                    ),
                    "attempted_providers": [str(name) for name in attempted],
                    "code": (
                        str(tool_result.get("code"))
                        if tool_result.get("code") is not None
                        else None
                    ),
                }

            stream_chunks = context.get("llm_stream_chunks", []) if isinstance(context, dict) else []
            if not isinstance(stream_chunks, list):
                stream_chunks = []
            if not stream_chunks:
                fallback_chunk = str(context.get("llm_output", "")) if isinstance(context, dict) else ""
                if fallback_chunk:
                    stream_chunks = [fallback_chunk]

            for chunk in stream_chunks:
                yield _format_sse_event("chunk", {"chunk": str(chunk)})

            yield _format_sse_event(
                "done",
                {
                    "task_id": str(result.get("task_id", "")),
                    "final_state": str(result.get("final_state", "")),
                    "llm_output": str(context.get("llm_output", "")) if isinstance(context, dict) else "",
                    "failure": failure_data,
                    "tool_preview": tool_preview,
                },
            )
        except Exception as exc:
            yield _format_sse_event("error", {"error": str(exc)})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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

        elapsed_ns_raw = payload.get("elapsed_ns")
        elapsed_ns = (
            int(elapsed_ns_raw)
            if isinstance(elapsed_ns_raw, (int, float, str))
            else None
        )
        start_offset_ns_raw = payload.get("start_offset_ns")
        start_offset_ns = (
            int(start_offset_ns_raw)
            if isinstance(start_offset_ns_raw, (int, float, str))
            else None
        )

        node_events.append(
            WorkflowNodeEvent(
                node_id=str(payload.get("node_id", "")),
                node_type=str(payload.get("node_type", "")),
                controller_state=str(payload.get("controller_state", "")),
                event_type=str(payload.get("event_type", "")),
                success=bool(payload.get("success", False)),
                task_id=str(payload.get("task_id")) if payload.get("task_id") is not None else None,
                elapsed_ns=elapsed_ns,
                start_offset_ns=start_offset_ns,
                error=str(payload.get("error")) if payload.get("error") is not None else None,
            )
        )

    indexed_node_events = list(enumerate(node_events))
    indexed_node_events.sort(
        key=lambda pair: (
            pair[1].start_offset_ns is None,
            int(pair[1].start_offset_ns) if pair[1].start_offset_ns is not None else 0,
            pair[0],
        )
    )
    node_events = [event for _, event in indexed_node_events]

    return WorkflowTelemetryResponse(
        task_id=task_id,
        workflow_graph=workflow_graph,
        workflow_execution_order=workflow_execution_order,
        node_events=node_events,
    )
