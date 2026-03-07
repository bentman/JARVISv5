from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.config.settings import (
    normalize_default_search_provider,
    normalize_hardware_profile,
    normalize_log_level,
)


class WorkflowGraphEdge(BaseModel):
    from_node: str
    to_node: str


class WorkflowGraph(BaseModel):
    nodes: list[str] = Field(default_factory=list)
    edges: list[WorkflowGraphEdge] = Field(default_factory=list)
    entry: str = ""


class WorkflowNodeEvent(BaseModel):
    node_id: str = ""
    node_type: str = ""
    controller_state: str = ""
    event_type: str = ""
    success: bool = False
    task_id: str | None = None
    elapsed_ns: int | None = None
    start_offset_ns: int | None = None
    error: str | None = None


class WorkflowTelemetryResponse(BaseModel):
    """v1 schema for workflow telemetry responses."""

    task_id: str
    workflow_graph: WorkflowGraph | dict[str, Any] = Field(default_factory=dict)
    workflow_execution_order: list[str] = Field(default_factory=list)
    node_events: list[WorkflowNodeEvent] = Field(default_factory=list)


class TaskFailureMetadata(BaseModel):
    reason: str | None = None
    attempted_providers: list[str] = Field(default_factory=list)
    code: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    final_state: str
    llm_output: str
    failure: TaskFailureMetadata | None = None


class MemorySearchItem(BaseModel):
    source: str
    content: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearchResponse(BaseModel):
    query: str
    semantic_results: list[MemorySearchItem] = Field(default_factory=list)
    episodic_results: list[MemorySearchItem] = Field(default_factory=list)


class SettingsResponse(BaseModel):
    """v1 schema for settings responses, aligned to current Settings model."""

    app_name: str | None = None
    debug: bool | None = None
    hardware_profile: str | None = None
    log_level: str | None = None
    model_path: str | None = None
    data_path: str | None = None
    backend_port: int | None = None

    # Future UI roadmap fields (optional until surfaced by backend settings model/API)
    redact_pii_queries: bool | None = None
    redact_pii_results: bool | None = None
    allow_external_search: bool | None = None
    default_search_provider: str | None = None
    cache_enabled: bool | None = None


class SettingsUpdateRequest(BaseModel):
    hardware_profile: str | None = None
    log_level: str | None = None
    allow_external_search: bool | None = None
    default_search_provider: str | None = None
    cache_enabled: bool | None = None

    @field_validator("hardware_profile")
    @classmethod
    def validate_hardware_profile(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_hardware_profile(value)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_log_level(value)

    @field_validator("default_search_provider")
    @classmethod
    def validate_default_search_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_default_search_provider(value)


class BudgetPeriod(BaseModel):
    limit_usd: float = 0.0
    spent_usd: float = 0.0
    remaining_usd: float = 0.0


class BudgetResponse(BaseModel):
    """v1 schema for budget responses."""

    daily: BudgetPeriod = Field(default_factory=BudgetPeriod)
    monthly: BudgetPeriod | None = None


class HardwareHealth(BaseModel):
    profile: str | None = None
    type: str | None = None
    cpu_count: int | None = None
    memory_gb: float | None = None


class ModelHealth(BaseModel):
    selected: str | None = None
    profile: str | None = None
    role: str | None = None


class CacheHealth(BaseModel):
    enabled: bool | None = None
    connected: bool | None = None


class DetailedHealthResponse(BaseModel):
    """v1 schema for detailed health responses."""

    status: str
    service: str
    hardware: HardwareHealth | None = None
    model: ModelHealth | None = None
    cache: CacheHealth | None = None
