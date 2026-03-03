# Milestone 9: UI Completion (Spec-Aligned) - Implementation Plan (REVISED v3)

**Date**: 2026-03-02  
**Status**: PLANNED - Revised per Agent feedback + tightening addendum  
**Prerequisites**: M1-M8 Complete ✅

---

## Agent Feedback Resolution

### Issues Addressed

| Issue | Agent Concern | Resolution |
|-------|---------------|------------|
| **A: No contract/versioning** | Frontend/backend drift, brittle tests | ✅ Task 9.0: API contracts first |
| **B: Settings inconsistency** | `Settings` vs raw env vars | ✅ Canonical config projection |
| **C: Budget internal access** | Private `_ledger` coupling | ✅ Public query helpers |
| **D: Polling-only workflow** | Not truly "live" | ✅ Phased: polling → SSE |
| **E: Heavy health checks** | Expensive polling overhead | ✅ Separate liveness/readiness/detail |

### Tightening Addendum (v3)

This revision applies four explicit tightening points:

1. **Canonical settings source is truly typed**: all UI-exposed settings are first modeled on `Settings`, then projected from `Settings` only.
2. **Budget semantics are explicit**: monthly means **rolling 30-day window** in UTC; no placeholder values in API examples.
3. **Detailed health cache semantics are explicit**: cache is **process-local** (per worker/process) and non-shared.
4. **"Live" wording is precise**: M9 provides **near-live polling**, while true streaming live updates remain deferred to SSE.

---

## Phase 1: API Contracts (NEW - Foundation)

### Task 9.0: Define API Response Schemas

**Status**: NEW REQUIREMENT (Agent feedback A)

**Objective**: Establish stable, versioned API contracts before implementation.

**File**: `backend/api/schemas.py` (NEW)

**Implementation**:
```python
"""
API Response Schemas for Milestone 9
Versioned contracts to prevent frontend/backend drift
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# Workflow Telemetry
class WorkflowNodeEvent(BaseModel):
    """Single DAG node event"""
    node_id: str
    node_type: str
    controller_state: str  # "PLAN", "EXECUTE", "VALIDATE"
    event_type: str  # "node_start", "node_end", "node_error"
    success: bool
    elapsed_ns: int | None = None
    error: str | None = None
    timestamp_offset_ns: int | None = Field(
        None,
        description="Monotonic offset from task start (for ordering)"
    )


class WorkflowGraphEdge(BaseModel):
    """DAG edge"""
    from_node: str
    to_node: str


class WorkflowGraph(BaseModel):
    """DAG structure"""
    nodes: list[str]
    edges: list[WorkflowGraphEdge]
    entry: str


class WorkflowTelemetryResponse(BaseModel):
    """GET /workflow/{task_id} response schema v1"""
    task_id: str
    graph: WorkflowGraph
    execution_order: list[str]
    node_events: list[WorkflowNodeEvent]


# Settings
class HardwareSettings(BaseModel):
    """Hardware configuration"""
    profile: str  # "Light", "Medium", "Heavy"


class PrivacySettings(BaseModel):
    """Privacy configuration"""
    redact_pii_queries: bool
    redact_pii_results: bool


class SearchSettings(BaseModel):
    """Search configuration"""
    allow_external: bool
    default_provider: str  # "searxng", "duckduckgo", "tavily"


class CacheSettings(BaseModel):
    """Cache configuration"""
    enabled: bool


class SettingsResponse(BaseModel):
    """GET /settings response schema v1"""
    hardware: HardwareSettings
    privacy: PrivacySettings
    search: SearchSettings
    cache: CacheSettings


# Budget
class BudgetPeriod(BaseModel):
    """Budget for a period (daily/monthly)"""
    limit_usd: float
    spent_usd: float
    remaining_usd: float


class BudgetResponse(BaseModel):
    """GET /budget response schema v1"""
    daily: BudgetPeriod
    monthly: BudgetPeriod


# Health (Extended)
class HardwareHealth(BaseModel):
    """Hardware status"""
    profile: str
    type: str  # "cpu", "cuda", "metal", "openvino"
    cpu_count: int
    memory_gb: float


class ModelHealth(BaseModel):
    """Model status"""
    selected: str | None
    profile: str
    role: str  # "chat", "code"


class CacheHealth(BaseModel):
    """Cache status"""
    enabled: bool
    connected: bool


class DetailedHealthResponse(BaseModel):
    """GET /health/detailed response schema v1"""
    status: str  # "ok"
    service: str  # "JARVISv5-backend"
    hardware: HardwareHealth
    model: ModelHealth
    cache: CacheHealth
```

**Validation**:
```python
# Test schema instantiation
def test_workflow_telemetry_schema():
    response = WorkflowTelemetryResponse(
        task_id="task-123",
        graph=WorkflowGraph(
            nodes=["router", "llm_worker"],
            edges=[WorkflowGraphEdge(from_node="router", to_node="llm_worker")],
            entry="router"
        ),
        execution_order=["router", "llm_worker"],
        node_events=[
            WorkflowNodeEvent(
                node_id="router",
                node_type="RouterNode",
                controller_state="PLAN",
                event_type="node_end",
                success=True,
                elapsed_ns=1000000,
                timestamp_offset_ns=0
            )
        ]
    )
    assert response.task_id == "task-123"
```

**Acceptance Criteria**:
- [ ] All response schemas defined as Pydantic models
- [ ] Version documented in docstrings (v1)
- [ ] Example instantiation tests pass
- [ ] No backend/frontend implementation yet (contracts only)

### Sub-Task 9.0.1: Endpoint Gap Map + Source-of-Truth Route Inventory

**Status**: NEW (course-correction prerequisite for 9.1+)

**Objective**: Lock an explicit map of required-vs-existing API routes before endpoint wiring.

**Scope**: Discovery/report only (no code changes).

**Current Registered Routes (verified)**:
- `GET /health` → `backend/api/main.py:41-43`
- `POST /task` → `backend/api/main.py:46-62`
- `GET /task/{task_id}` → `backend/api/main.py:65-72`
- `FastAPI` app declaration → `backend/api/main.py:12`
- Additional routers: **none** (`APIRouter` / `include_router` not present in registered API surface).

**Required Endpoint Gap Map (M9 backend APIs)**:

| Required endpoint | Expected schema | Exists now? | Current route if different | Handler/capability location | Notes |
|---|---|---|---|---|---|
| `/settings` | `SettingsResponse` | No | None | `backend/config/settings.py` | Typed settings source exists; no API projection route yet. |
| `/budget` | `BudgetResponse` | No | None | `backend/search/budget.py` | Budget ledger/config exist; no API summary route yet. |
| `/health/detailed` | `DetailedHealthResponse` | No | Near-miss: `/health` | `backend/api/main.py:41-43` | Only liveness payload exists today (`status`, `service`). |
| `/health/ready` | roadmap health-tier readiness payload | No | Near-miss: `/health` | `backend/api/main.py:41-43` | Readiness tier is planned but absent. |
| `/workflow/{task_id}` | `WorkflowTelemetryResponse` | No | Near-miss: `/task/{task_id}` | `backend/api/main.py:65-72`, `backend/controller/controller_service.py` | Workflow graph/ordering may exist in task state; no dedicated telemetry contract route. |

**Recommended tests to add/adjust for this sub-task**:
- None (discovery-only; this is an execution planning artifact).

**Acceptance Criteria**:
- [ ] Gap map captured in roadmap with exact file:line route references
- [ ] Required endpoints and expected schemas explicitly listed
- [ ] Near-miss routes/capabilities identified for each missing endpoint

### Sub-Task 9.0.2: Add `GET /settings` (Schema-Aligned Projection)

**Objective**: Add `GET /settings` returning `SettingsResponse` with keys aligned to `backend/config/settings.py`.

**Current State**:
- Missing endpoint.
- Source capability exists in typed `Settings` model (`backend/config/settings.py`).

**Required route/handler target**:
- Route: `GET /settings`
- Response model: `SettingsResponse`
- File: `backend/api/main.py`

**Execution notes**:
- Use `Settings()` as source of truth for current values.
- Keep response shape aligned with existing schema fields in `backend/api/schemas.py`.
- If a field is not available from current settings model, return schema optional defaults (no fabricated runtime values).

**Recommended tests to add/adjust**:
- Extend or add API tests (FastAPI `TestClient`) to verify:
  - `200` response
  - top-level keys expected by `SettingsResponse`
  - representative values reflect current settings defaults/overrides

**Acceptance Criteria**:
- [ ] `GET /settings` exists and returns `SettingsResponse`
- [ ] Handler uses typed settings source (no ad-hoc drift)
- [ ] API test coverage added/updated for happy-path response keys

### Sub-Task 9.0.3: Add `GET /budget` (Schema-Aligned Summary)

**Objective**: Add `GET /budget` returning `BudgetResponse` from budget ledger/config abstractions.

**Current State**:
- Missing endpoint.
- Budget capability exists in `backend/search/budget.py` (`SearchBudgetConfig`, `SearchBudgetLedger`).

**Required route/handler target**:
- Route: `GET /budget`
- Response model: `BudgetResponse`
- File: `backend/api/main.py`

**Execution notes**:
- Build response from existing budget module capabilities.
- Keep semantics explicit for daily and monthly fields in returned payload.
- Avoid introducing private-structure coupling if public helpers are present/added.

**Recommended tests to add/adjust**:
- API test for:
  - `200` response
  - presence of `daily` and `monthly`
  - presence of `limit_usd`, `spent_usd`, `remaining_usd` in each period object

**Acceptance Criteria**:
- [ ] `GET /budget` exists and returns `BudgetResponse`
- [ ] Response contract is schema-valid with deterministic numeric fields
- [ ] API test coverage added/updated for budget keys

### Sub-Task 9.0.4: Add `GET /health/detailed` (Detailed Diagnostics Contract)

**Objective**: Add detailed health endpoint returning `DetailedHealthResponse` without altering existing `/health` behavior.

**Current State**:
- Missing endpoint.
- Near-miss exists: `GET /health` currently returns `{status, service}` only.

**Required route/handler target**:
- Route: `GET /health/detailed`
- Response model: `DetailedHealthResponse`
- File: `backend/api/main.py`

**Execution notes**:
- Preserve current `GET /health` response shape and behavior.
- Populate `hardware`, `model`, `cache` blocks using existing backend services where available.
- If any sub-block data is unavailable, use schema optional behavior instead of fabricated values.

**Recommended tests to add/adjust**:
- API test for:
  - `200` response
  - top-level keys: `status`, `service`
  - presence of detailed blocks (`hardware`, `model`, `cache`) when available

**Acceptance Criteria**:
- [ ] `GET /health/detailed` exists and returns `DetailedHealthResponse`
- [ ] Existing `GET /health` remains unchanged and passing existing tests
- [ ] API test coverage added/updated for detailed health contract

### Sub-Task 9.0.5: Add `GET /health/ready` (Readiness Tier)

**Objective**: Add readiness endpoint for M9 health-tier split, separate from liveness and detailed diagnostics.

**Current State**:
- Missing endpoint.
- Only liveness endpoint currently exists (`GET /health`).

**Required route/handler target**:
- Route: `GET /health/ready`
- Response model: optional/simple dict contract (roadmap-defined readiness payload)
- File: `backend/api/main.py`

**Execution notes**:
- Keep liveness endpoint lightweight and unchanged.
- Readiness should validate minimum backend-serving prerequisites (for example settings/memory instantiation path).
- Preserve deterministic fail-safe response behavior.

**Recommended tests to add/adjust**:
- API test for:
  - success path (`ready: true` or equivalent)
  - fail path handling (if injectable in tests)
  - no regression on `/health`

**Acceptance Criteria**:
- [ ] `GET /health/ready` exists with stable readiness payload
- [ ] Readiness check does not break existing liveness behavior
- [ ] API test coverage added/updated for readiness route

### Sub-Task 9.0.6: Add `GET /workflow/{task_id}` (Telemetry Contract Route)

**Objective**: Add dedicated workflow telemetry endpoint returning `WorkflowTelemetryResponse`.

**Current State**:
- Missing endpoint.
- Near-miss route exists: `GET /task/{task_id}` returns full task state.
- Workflow telemetry ingredients exist in runtime state/logging:
  - task `workflow_graph` and `workflow_execution_order` persistence
  - `dag_node_event` logging in controller service

**Required route/handler target**:
- Route: `GET /workflow/{task_id}`
- Response model: `WorkflowTelemetryResponse`
- File: `backend/api/main.py`

**Execution notes**:
- Keep `/task/{task_id}` behavior unchanged.
- Build telemetry response from existing task-state + episodic DAG event records.
- Preserve current 404 behavior for unknown task IDs.

**Recommended tests to add/adjust**:
- API test(s) for:
  - 200 for known task, 404 for unknown task
  - top-level keys: `task_id`, `workflow_graph`, `workflow_execution_order`, `node_events`
  - deterministic ordering assertion for `node_events` (based on available offset/timing field)

**Acceptance Criteria**:
- [ ] `GET /workflow/{task_id}` exists and returns `WorkflowTelemetryResponse`
- [ ] Unknown task returns `404` consistent with existing API semantics
- [ ] API test coverage added/updated for success + not-found + event ordering

---

## Phase 2: Backend - Settings Consistency (Agent feedback B)

### Task 9.1: Centralized Config Projection

**Status**: REVISED (Agent feedback B)

**Objective**: Single canonical source for settings, no drift between `Settings` and env vars.

**File**: `backend/config/settings.py` (MODIFY)

**Typed Settings Additions (required before projection helper)**:
```python
class Settings(BaseSettings):
    # ... existing fields ...
    REDACT_PII_QUERIES: bool = True
    REDACT_PII_RESULTS: bool = False
    ALLOW_EXTERNAL_SEARCH: bool = False
    DEFAULT_SEARCH_PROVIDER: str = "duckduckgo"
    CACHE_ENABLED: bool = False
```

**New Helper**:
```python
def get_safe_config_projection(settings: Settings) -> dict:
    """
    Canonical config projection for API exposure.
    
    Single source of truth - no direct os.getenv in API layer.
    Excludes secrets (API keys, passwords).
    """
    return {
        "hardware": {
            "profile": settings.HARDWARE_PROFILE,
        },
        "privacy": {
            "redact_pii_queries": settings.REDACT_PII_QUERIES,
            "redact_pii_results": settings.REDACT_PII_RESULTS,
        },
        "search": {
            "allow_external": settings.ALLOW_EXTERNAL_SEARCH,
            "default_provider": settings.DEFAULT_SEARCH_PROVIDER,
        },
        "cache": {
            "enabled": settings.CACHE_ENABLED,
        }
    }
```

**File**: `backend/api/main.py` (MODIFY)

**Implementation**:
```python
from backend.api.schemas import SettingsResponse
from backend.config.settings import get_safe_config_projection


@app.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    """
    Retrieve current configuration (read-only, safe).
    
    Returns typed schema, no secrets exposed.
    Uses canonical config projection.
    """
    settings = Settings()
    projection = get_safe_config_projection(settings)
    
    return SettingsResponse(
        hardware=HardwareSettings(**projection["hardware"]),
        privacy=PrivacySettings(**projection["privacy"]),
        search=SearchSettings(**projection["search"]),
        cache=CacheSettings(**projection["cache"])
    )
```

**Acceptance Criteria**:
- [ ] All UI-exposed settings fields exist on typed `Settings`
- [ ] Single config source (`get_safe_config_projection(settings)`)
- [ ] No direct `os.getenv` usage in settings projection or API layer
- [ ] Response validated against schema
- [ ] Test: Settings returned match actual runtime config

---

## Phase 3: Backend - Budget Public API (Agent feedback C)

### Task 9.2: Budget Query Helpers

**Status**: REVISED (Agent feedback C)

**Objective**: Expose public budget queries, avoid private `_ledger` access.

**File**: `backend/search/budget.py` (MODIFY)

**New Public Methods**:
```python
class SearchBudgetLedger:
    # ... existing methods ...
    
    def get_daily_summary(self, date_key: str | None = None) -> dict:
        """
        Public API: Daily budget summary.
        
        Returns:
            {
                "date_key": str,
                "limit_usd": float,
                "spent_usd": float,
                "remaining_usd": float
            }
        """
        key = date_key or self.today_key()
        # Uses public APIs only; no private _ledger access.
        return {
            "date_key": key,
            "spent_usd": self.get_spent(key),
        }

    def get_rolling_30d_spent(self, end_date_key: str | None = None) -> float:
        """
        Public API: rolling 30-day spend window (UTC), inclusive of end date.
        """
        # Deterministic window semantics for monthly UI/API reporting.
        end_key = end_date_key or self.today_key()
        end_date = datetime.fromisoformat(end_key).date()
        monthly_spent = 0.0
        for days_ago in range(30):
            day = (end_date - timedelta(days=days_ago)).isoformat()
            monthly_spent += self.get_spent(day)
        return round(monthly_spent, 6)

    def get_monthly_summary(self, monthly_limit_usd: float, end_date_key: str | None = None) -> dict:
        """
        Public API: monthly summary using rolling 30-day UTC semantics.
        """
        spent = self.get_rolling_30d_spent(end_date_key=end_date_key)
        remaining = max(0.0, float(monthly_limit_usd) - spent)
        return {
            "window": "rolling_30d_utc",
            "limit_usd": float(monthly_limit_usd),
            "spent_usd": spent,
            "remaining_usd": round(remaining, 6),
        }
```

**File**: `backend/api/main.py` (MODIFY)

**Implementation**:
```python
from backend.api.schemas import BudgetResponse, BudgetPeriod
from backend.search.budget import SearchBudgetLedger, SearchBudgetConfig


@app.get("/budget", response_model=BudgetResponse)
def get_budget() -> BudgetResponse:
    """
    Retrieve budget summary using public API only.
    
    No access to private _ledger internals.
    """
    # Load config from env
    config = SearchBudgetConfig(daily_limit_usd=float(os.getenv("DAILY_BUDGET_USD", "0.0")))
    monthly_limit_usd = float(os.getenv("MONTHLY_BUDGET_USD", "0.0"))
    
    ledger = SearchBudgetLedger()
    
    # Use public methods only
    daily = ledger.get_daily_summary()
    monthly = ledger.get_monthly_summary(monthly_limit_usd=monthly_limit_usd)
    
    return BudgetResponse(
        daily=BudgetPeriod(
            limit_usd=config.daily_limit_usd,
            spent_usd=daily["spent_usd"],
            remaining_usd=ledger.remaining_budget_usd(
                daily["date_key"],
                config.daily_limit_usd
            )
        ),
        monthly=BudgetPeriod(
            limit_usd=monthly["limit_usd"],
            spent_usd=monthly["spent_usd"],
            remaining_usd=monthly["remaining_usd"]
        )
    )
```

**Acceptance Criteria**:
- [ ] Budget module exposes public `get_daily_summary()`
- [ ] Budget module exposes public `get_monthly_summary()`
- [ ] API endpoint uses public methods only (no `._ledger`)
- [ ] Monthly semantics explicitly defined as `rolling_30d_utc`
- [ ] No placeholder values in budget API examples
- [ ] Deterministic precision policy documented and tested (e.g., 6 decimal places)
- [ ] Test: Monthly rolling window and boundary dates are correct

---

## Phase 4: Backend - Health Endpoint Strategy (Agent feedback E)

### Task 9.3: Separate Health Endpoints

**Status**: REVISED (Agent feedback E)

**Objective**: Separate liveness, readiness, and detailed diagnostics.

**File**: `backend/api/main.py` (MODIFY)

**Three-Tier Health**:
```python
from backend.api.schemas import DetailedHealthResponse


@app.get("/health")
def health() -> dict:
    """
    Liveness check - fast, minimal overhead.
    
    Returns {"status": "ok"} if process is alive.
    """
    return {"status": "ok", "service": "JARVISv5-backend"}


@app.get("/health/ready")
def health_ready() -> dict:
    """
    Readiness check - indicates if backend can serve requests.
    
    Checks:
    - Memory manager can be instantiated
    - Settings can be loaded
    
    Returns {"ready": true/false}
    """
    try:
        settings = Settings()
        memory = _build_memory_manager(settings)
        return {"ready": True, "service": "JARVISv5-backend"}
    except Exception as exc:
        return {"ready": False, "error": str(exc)}


# Cache detailed health (30s TTL)
_detailed_health_cache = None
_detailed_health_timestamp = 0.0


@app.get("/health/detailed", response_model=DetailedHealthResponse)
def health_detailed() -> DetailedHealthResponse:
    """
    Detailed diagnostics - expensive, cached for 30s.
    
    Returns hardware, model, cache status.
    UI should poll this infrequently (30s+).

    NOTE: cache is process-local (per worker/process) and not shared.
    """
    global _detailed_health_cache, _detailed_health_timestamp
    
    import time
    now = time.time()
    
    # Return cached if fresh
    if _detailed_health_cache and (now - _detailed_health_timestamp) < 30.0:
        return _detailed_health_cache
    
    # Recompute
    settings = Settings()
    hardware_service = HardwareService()
    model_registry = ModelRegistry()
    
    hardware_type = hardware_service.detect_hardware_type().value
    profile = hardware_service.get_hardware_profile()
    
    import psutil
    cpu_count = psutil.cpu_count(logical=True) or 0
    memory_gb = psutil.virtual_memory().total / (1024**3)
    
    selected_model = model_registry.select_model(
        profile=profile,
        hardware=hardware_type,
        role="chat"
    )
    
    from backend.cache.redis_client import create_default_redis_client
    cache_client = create_default_redis_client()
    cache_health = cache_client.health_check()
    
    result = DetailedHealthResponse(
        status="ok",
        service="JARVISv5-backend",
        hardware=HardwareHealth(
            profile=profile,
            type=hardware_type,
            cpu_count=cpu_count,
            memory_gb=round(memory_gb, 1),
        ),
        model=ModelHealth(
            selected=selected_model,
            profile=profile,
            role="chat",
        ),
        cache=CacheHealth(
            enabled=cache_health["enabled"],
            connected=cache_health["connected"],
        )
    )
    
    # Cache for 30s
    _detailed_health_cache = result
    _detailed_health_timestamp = now
    
    return result
```

**Acceptance Criteria**:
- [ ] GET /health - Fast liveness (<1ms)
- [ ] GET /health/ready - Readiness with instantiation check
- [ ] GET /health/detailed - Expensive diagnostics cached 30s
- [ ] `/health/detailed` cache behavior documented as process-local
- [ ] Frontend polls /health every 5s, /health/detailed every 30s
- [ ] Test: Cache works within one process (same result returned within 30s)

---

## Phase 5: Backend - Workflow Telemetry (Stable Events)

### Task 9.4: Workflow Endpoint with Deterministic Events

**Status**: REVISED (Agent feedback A, stable schema)

**Objective**: Return workflow graph + DAG events with stable ordering for near-live polling UX.

**File**: `backend/api/main.py` (MODIFY)

**Implementation**:
```python
from backend.api.schemas import (
    WorkflowTelemetryResponse,
    WorkflowGraph,
    WorkflowGraphEdge,
    WorkflowNodeEvent
)


@app.get("/workflow/{task_id}", response_model=WorkflowTelemetryResponse)
def get_workflow(task_id: str) -> WorkflowTelemetryResponse:
    """
    Retrieve workflow graph and DAG node events.
    
    Returns:
    - Workflow graph from task state
    - Node events from episodic DB (ordered by timestamp_offset_ns)
    """
    settings = Settings()
    memory = _build_memory_manager(settings)
    
    # Get task state for workflow_graph
    task_state = memory.get_task_state(task_id)
    if task_state is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    workflow_graph_dict = task_state.get("workflow_graph", {})
    execution_order = task_state.get("workflow_execution_order", [])
    
    # Parse graph
    graph = WorkflowGraph(
        nodes=workflow_graph_dict.get("nodes", []),
        edges=[
            WorkflowGraphEdge(**edge)
            for edge in workflow_graph_dict.get("edges", [])
        ],
        entry=workflow_graph_dict.get("entry", "")
    )
    
    # Query episodic DB for dag_node_event logs
    decisions = memory.episodic.search_decisions(
        query="dag_node_event",
        task_id=task_id,
        limit=100
    )
    
    node_events = []
    for decision in decisions:
        if decision["action_type"] != "dag_node_event":
            continue
        try:
            payload = json.loads(decision["content"])
            node_events.append(
                WorkflowNodeEvent(
                    node_id=payload.get("node_id", ""),
                    node_type=payload.get("node_type", ""),
                    controller_state=payload.get("controller_state", ""),
                    event_type=payload.get("event_type", ""),
                    success=payload.get("success", False),
                    elapsed_ns=payload.get("elapsed_ns"),
                    error=payload.get("error"),
                    timestamp_offset_ns=payload.get("start_offset_ns"),
                )
            )
        except Exception:
            continue
    
    # Sort by timestamp_offset_ns for deterministic ordering
    node_events.sort(key=lambda e: e.timestamp_offset_ns or 0)
    
    return WorkflowTelemetryResponse(
        task_id=task_id,
        graph=graph,
        execution_order=execution_order,
        node_events=node_events,
    )
```

**Acceptance Criteria**:
- [ ] Returns typed `WorkflowTelemetryResponse`
- [ ] Events sorted by `timestamp_offset_ns` (monotonic)
- [ ] 404 for non-existent tasks
- [ ] Test: Event ordering is deterministic

---

## Phase 6: Frontend - Component Structure (Agent feedback componentization)

### Task 9.5: API Client Extension

**Status**: REVISED (centralized API client)

**Objective**: Extend `taskClient.js` with new endpoints.

**File**: `frontend/src/api/taskClient.js` (MODIFY)

**New Methods**:
```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ... existing methods ...

export async function getWorkflow(taskId) {
  const response = await fetch(`${API_BASE_URL}/workflow/${taskId}`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export async function getSettings() {
  const response = await fetch(`${API_BASE_URL}/settings`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export async function getBudget() {
  const response = await fetch(`${API_BASE_URL}/budget`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export async function getDetailedHealth() {
  const response = await fetch(`${API_BASE_URL}/health/detailed`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}
```

**Acceptance Criteria**:
- [ ] All M9 endpoints in centralized client
- [ ] Error handling consistent
- [ ] Used by all components (no inline fetch)

---

### Task 9.6: WorkflowVisualizer Component

**Status**: UNCHANGED (uses centralized client)

**File**: `frontend/src/components/WorkflowVisualizer.jsx` (NEW)

**Changes from original**:
```jsx
import { getWorkflow } from '../api/taskClient'

// ... component implementation ...

useEffect(() => {
  if (!taskId || !isOpen) return
  
  const fetchWorkflow = async () => {
    setLoading(true)
    try {
      const data = await getWorkflow(taskId)  // Use centralized client
      setWorkflow(data)
    } catch (err) {
      console.error('Failed to fetch workflow:', err)
    } finally {
      setLoading(false)
    }
  }
  
  fetchWorkflow()
}, [taskId, isOpen])
```

**Acceptance Criteria**: Same as original plan

---

### Task 9.7: SettingsPanel Component

**Status**: REVISED (uses centralized client + schema types)

**File**: `frontend/src/components/SettingsPanel.jsx` (NEW)

**Changes from original**:
```jsx
import { getSettings, getBudget } from '../api/taskClient'

// ... component implementation ...

useEffect(() => {
  if (!isOpen) return
  
  const fetchSettings = async () => {
    setLoading(true)
    try {
      const [settingsData, budgetData] = await Promise.all([
        getSettings(),
        getBudget()
      ])
      setSettings(settingsData)
      setBudget(budgetData)
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    } finally {
      setLoading(false)
    }
  }
  
  fetchSettings()
  const interval = setInterval(fetchSettings, 10000)
  return () => clearInterval(interval)
}, [isOpen])
```

**Acceptance Criteria**: Same as original plan

---

### Task 9.8: Enhanced Status Indicators

**Status**: REVISED (uses /health/detailed with 30s polling)

**File**: `frontend/src/App.jsx` (MODIFY)

**Changes from original**:
```jsx
import { getHealth, getDetailedHealth } from './api/taskClient'

// Separate intervals for liveness vs detailed
useEffect(() => {
  // Fast liveness check (5s)
  const checkLiveness = async () => {
    try {
      await getHealth()
      setIsBackendOnline(true)
    } catch {
      setIsBackendOnline(false)
      setDetailedHealth(null)
    }
  }
  
  // Slow detailed check (30s)
  const checkDetailed = async () => {
    try {
      const data = await getDetailedHealth()
      setDetailedHealth(data)
    } catch {
      setDetailedHealth(null)
    }
  }
  
  checkLiveness()
  checkDetailed()
  
  const livenessInterval = setInterval(checkLiveness, 5000)
  const detailedInterval = setInterval(checkDetailed, 30000)
  
  return () => {
    clearInterval(livenessInterval)
    clearInterval(detailedInterval)
  }
}, [])
```

**Acceptance Criteria**:
- [ ] GET /health polled every 5s (fast)
- [ ] GET /health/detailed polled every 30s (cached)
- [ ] Graceful degradation when detailed unavailable

---

## Phase 7: Future - SSE Workflow Events (Agent feedback D)

### Task 9.9: SSE Endpoint (Post-M9, Optional)

**Status**: DEFERRED (Phase 2 enhancement)

**Objective**: True live workflow events without websocket complexity.

**File**: `backend/api/main.py` (FUTURE)

**Sketch**:
```python
from fastapi.responses import StreamingResponse

@app.get("/workflow/{task_id}/events")
async def workflow_events_stream(task_id: str):
    """
    Server-Sent Events stream for workflow updates.
    
    Sends node events as they occur.
    Client reconnects if connection drops.
    """
    async def event_generator():
        # Subscribe to episodic event stream
        # Yield SSE-formatted events
        yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Deferred Rationale**: M9 uses near-live polling. SSE enables true live streaming and is deferred to reduce M9 complexity. Revisit in M10 if near-live polling is insufficient.

---

## Revised Implementation Order

**Phase-Based Sequence**:

1. **Phase 1**: Task 9.0 - API Contracts (schemas.py)
2. **Phase 2**: Task 9.1 - Settings consistency
3. **Phase 3**: Task 9.2 - Budget public API
4. **Phase 4**: Task 9.3 - Health tiers (liveness/ready/detailed)
5. **Phase 5**: Task 9.4 - Workflow telemetry endpoint
6. **Phase 6**: Tasks 9.5-9.8 - Frontend components
7. **Phase 7**: Task 9.9 - SSE (deferred to post-M9)

**Rationale**:
- Contracts first (prevent drift)
- Backend consistency fixes before new endpoints
- Frontend last (consumes stable APIs)
- SSE deferred (optional enhancement)

---

## Testing Strategy (Revised)

### Backend Unit Tests

**New Test Files**:
1. `tests/unit/test_api_schemas.py` - Schema instantiation
2. `tests/unit/test_api_workflow_endpoint.py` - Workflow telemetry
3. `tests/unit/test_api_settings_endpoint.py` - Settings + budget
4. `tests/unit/test_api_health_endpoints.py` - All 3 health tiers
5. `tests/unit/test_budget_public_api.py` - Public query helpers

**Coverage**:
- All schemas instantiate from example data
- Settings endpoint returns values matching `Settings` object
- Budget endpoint uses public API only (no `._ledger`)
- Health detailed endpoint returns cached result within 30s
- Workflow events sorted by `timestamp_offset_ns`

### Frontend Tests (Manual)

**Integration Checklist**:
```bash
# 1. Start services
docker compose up -d

# 2. Basic health
curl http://localhost:8000/health
# {"status":"ok","service":"JARVISv5-backend"}

# 3. Readiness
curl http://localhost:8000/health/ready
# {"ready":true,"service":"JARVISv5-backend"}

# 4. Detailed health (cached)
curl http://localhost:8000/health/detailed
# {hardware, model, cache} within 30s cache window

# 5. Settings
curl http://localhost:8000/settings
# {hardware, privacy, search, cache}

# 6. Budget
curl http://localhost:8000/budget
# {daily, monthly} with spend/limit/remaining

# 7. Send task
curl -X POST http://localhost:8000/task -d '{"user_input":"test"}'
# {"task_id":"task-xxx",...}

# 8. Get workflow
curl http://localhost:8000/workflow/task-xxx
# {graph, execution_order, node_events}

# 9. Open UI
http://localhost:3000

# 10. Test components
- Click "Workflow" → See node execution
- Click "Settings" → See config + budget
- Verify header shows model + cache status
```

---

## Success Criteria (Revised)

**M9 COMPLETE when**:
- ✅ Task 9.0: API schemas defined + validated
- ✅ Task 9.1: Settings endpoint uses canonical projection
- ✅ Task 9.2: Budget endpoint uses public API only
- ✅ Task 9.3: 3-tier health (liveness/ready/detailed)
- ✅ Task 9.4: Workflow endpoint returns typed schema
- ✅ Task 9.5: API client centralized
- ✅ Task 9.6: WorkflowVisualizer component working
- ✅ Task 9.7: SettingsPanel component working
- ✅ Task 9.8: Enhanced status in header
- ✅ All unit tests passing
- ✅ Manual integration checklist complete
- ✅ CHANGE_LOG entry with evidence
- ✅ SYSTEM_INVENTORY entry

---

## Explicitly Deferred (Not M9)

**Post-M9 Enhancements**:
1. **SSE Workflow Events** (Task 9.9) - Optional, complexity vs value
2. **Settings Write API** (`POST /settings`) - Requires auth/validation
3. **Voice Panel** - M11 (optional milestone)
4. **Interactive Graph** - Advanced visualization

---

## CHANGE_LOG Entry Template (Revised)

```
- 2026-03-XX HH:MM
  - Summary: Completed Milestone 9 UI Completion with typed API contracts, workflow visualizer, settings panel, and 3-tier health endpoints aligned to Project.md §11.2.
  - Scope: `backend/api/schemas.py`, `backend/api/main.py`, `backend/config/settings.py`, `backend/search/budget.py`, `frontend/src/components/WorkflowVisualizer.jsx`, `frontend/src/components/SettingsPanel.jsx`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`, `tests/unit/test_api_schemas.py`, `tests/unit/test_api_workflow_endpoint.py`, `tests/unit/test_api_settings_endpoint.py`, `tests/unit/test_api_health_endpoints.py`.
  - Key behaviors:
    - Pydantic schemas for all M9 endpoints (versioned v1 contracts).
    - GET /health: Fast liveness check (<1ms).
    - GET /health/ready: Readiness with instantiation check.
    - GET /health/detailed: Expensive diagnostics cached 30s (hardware, model, cache).
    - GET /workflow/{task_id}: Typed schema with deterministic event ordering (timestamp_offset_ns).
    - GET /settings: Canonical config projection (single source, no drift).
    - GET /budget: Public API only (no private _ledger access).
    - WorkflowVisualizer: Live node execution display with status (pending/running/completed/error).
    - SettingsPanel: Read-only config + budget with 10s auto-refresh.
    - Enhanced status: Header shows model + cache (30s polling).
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_api_schemas.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
    - Manual integration: All 10 checklist items verified (health endpoints, settings, budget, workflow, UI components).
```

---

**Plan Version**: 3.0 (REVISED - Agent Feedback Incorporated + Tightening Addendum)  
**Target Milestone**: M9 - UI Completion (Spec-Aligned)  
**Prerequisites**: M1-M8 Complete  
**Estimated Effort**: 9 tasks (8 implementation + 1 deferred), ~25-30 hours  
**Confidence**: VERY HIGH (contracts-first, phased approach, no brittle coupling)