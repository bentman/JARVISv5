# SYSTEM_INVENTORY.md
> Authoritative capability ledger. This is not a roadmap or config reference. 
> Inventory entries must reflect only observable artifacts in this repository: files, directories, executable code, configuration, scripts, and explicit UI text. 
> Do not include intent, design plans, or inferred behavior.

## Rules
- One component entry = one capability or feature observed in the repository.
- New capabilities go at the top under `## Inventory` and above `## Observed Initial Inventory`.
- Corrections or clarifications go only below the `## Appendix` section.
- Entries must include:

- Capability: **Brief Descriptive Component Name** 
  - Date/Time
  - State: Planned, Implemented, Verified, Deferred
  - Location: `Relative File Path(s)`
  - Validation: Method &/or `Relative Script Path(s)`
  - Notes: 
    - Optional (3 lines max).

## States
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command)
- Deferred: intentionally postponed (reason noted)

## Inventory

- Capability: Milestone 18 — Semantic Delete/Retrieval Settings/Context Observability Surface with Milestone-Close Validation
  - 2026-03-19 11:23
  - State: Verified
  - Location: `backend/memory/semantic_store.py`, `backend/memory/memory_manager.py`, `backend/api/main.py`, `backend/api/schemas.py`, `backend/config/settings.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/context_builder_node.py`, `frontend/src/components/MemoryPanel.jsx`, `frontend/src/components/SettingsPanel.jsx`, `frontend/src/api/taskClient.js`, `tests/unit/test_api_memory_search.py`, `tests/unit/test_semantic_store.py`, `tests/unit/test_context_builder_retrieval.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_memory_search.py tests/unit/test_semantic_store.py tests/unit/test_context_builder_retrieval.py tests/unit/test_api_settings.py tests/unit/test_controller_service_integration.py -q`; `backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`; `npm --prefix frontend run build`
  - Notes:
    - Repository/runtime artifacts expose semantic-memory delete by `entry_id`, stable delete key projection via `metadata.id`, and post-delete index rebuild behavior that preserves non-deleted semantic retrievability.
    - Context-builder execution context includes deterministic `retrieved_context_injected` observability.
    - Retrieval settings are exposed through backend config + `/settings` and surfaced in frontend Settings UI; semantic delete is surfaced in frontend Memory UI.

- Capability: Milestone 17 — Privacy Redaction Settings-to-Execution Surface and Validation Coverage
  - 2026-03-19 07:07
  - State: Verified
  - Location: `backend/config/settings.py`, `backend/api/schemas.py`, `backend/api/main.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/llm_worker_node.py`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_config.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_nodes.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py -q`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_settings.py tests/unit/test_api_schemas.py -q`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_nodes.py tests/unit/test_controller_service_integration.py -q`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`; `backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`; `npm --prefix frontend run build`
  - Notes:
    - Repository artifacts expose editable privacy redaction flags in config/settings and in the frontend Settings UI.
    - `/settings` supports read/write projection for both redaction flags.
    - Runtime/test artifacts verify query-side prompt redaction plus result-side redaction before assistant persistence and semantic write, including combined-path milestone-close coverage.

- Capability: Milestone 16.2 — Ollama Escalation Configuration, Provider Execution, Controller Fallback, and Settings UI Surface
  - 2026-03-14 22:08
  - State: Verified
  - Location: `backend/config/settings.py`, `backend/api/schemas.py`, `backend/api/main.py`, `.env.example`, `docker-compose.yml`, `backend/models/providers/ollama_provider.py`, `backend/models/providers/__init__.py`, `backend/controller/controller_service.py`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_config.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_escalation_providers.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py tests/unit/test_api_settings.py -q`; `docker compose config`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py -q`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`; `npm --prefix frontend run build`; `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py tests/unit/test_controller_service_integration.py -q`; `backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
  - Notes:
    - Repository artifacts include Ollama host escalation config projection/edit constraints, compose host-gateway support, Ollama provider implementation, controller local->Ollama pre-cloud fallback behavior, and frontend settings controls for Ollama escalation.

- Capability: Milestone 16 — Escalation Provider Execution Layer (T16.1–T16.4)
  - 2026-03-13 15:15
  - State: Verified
  - Location: `backend/requirements.txt` (Dependencies: T16.1), `backend/models/providers/__init__.py`, `backend/models/providers/anthropic_provider.py`, `backend/models/providers/openai_provider.py`, `backend/models/providers/gemini_provider.py`, `backend/models/providers/grok_provider.py`, `backend/controller/controller_service.py` (Backend: T16.2/T16.2.a/T16.3), `tests/unit/test_escalation_providers.py`, `tests/unit/test_controller_service_integration.py` (Tests/Validation: T16.4)
  - Validation: `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
  - Notes:
    - Dependencies, provider execution implementations (including Gemini SDK migration), controller registry population, and milestone coverage verification are present as observable repository artifacts.

- Capability: Milestone 15 — Model Escalation Config/Policy/Controller/API/UI Surface and Acceptance Coverage (T15.1–T15.7)
  - 2026-03-12 13:47
  - State: Verified
  - Location: `.env`, `.env.example`, `backend/config/api_keys.py`, `backend/config/settings.py`, `backend/models/escalation_policy.py`, `backend/models/__init__.py`, `backend/controller/controller_service.py`, `backend/api/main.py`, `backend/api/schemas.py`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_api_keys.py`, `tests/unit/test_escalation_policy.py`, `tests/unit/test_controller_service_integration.py`, `tests/unit/test_api_settings.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`; `npm --prefix frontend run build`
  - Notes:
    - Environment/Config: T15.1/T15.3; Backend: T15.2/T15.4/T15.5 (including corrective escalation settings API contract alignment); Frontend: T15.6 (including first-load dirty-state correction); Tests/Validation: T15.7.

- Capability: Milestone 14 — Search Provider Tiering, Typed Search Config Projection, Tier Policy Enforcement, SearchWebNode Graph Routing, and Consolidation Coverage (T14.1–T14.6)
  - 2026-03-12 07:03
  - State: Verified
  - Location: `backend/search/providers/base.py`, `backend/search/providers/searxng.py`, `backend/search/providers/ddg.py`, `backend/search/providers/tavily.py`, `backend/config/settings.py`, `backend/api/main.py`, `backend/api/schemas.py`, `backend/search/policy.py`, `backend/workflow/nodes/search_web_node.py`, `backend/workflow/__init__.py`, `backend/controller/controller_service.py`, `tests/unit/test_search_provider_contracts.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_config.py`, `tests/unit/test_search_policy.py`, `tests/unit/test_search_web_node.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
  - Notes:
    - Backend: T14.1/T14.2/T14.3/T14.4/T14.5; Tests/Validation: T14.6.

- Capability: Milestone 13 — Research Intent Routing, Memory API Completion, Validator Depth, and Memory Search Panel (T13.1–T13.4)
  - 2026-03-07 09:01
  - State: Verified
  - Location: `backend/api/main.py`, `backend/api/schemas.py`, `tests/unit/test_api_memory_search.py`, `backend/workflow/nodes/router_node.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/validator_node.py`, `tests/unit/test_nodes.py`, `tests/unit/test_controller_service_integration.py`, `frontend/src/components/MemoryPanel.jsx`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`; `npm --prefix frontend run build`
  - Notes:
    - Backend: T13.1/T13.2/T13.3; Frontend: T13.4.

- Capability: Milestone 12 — Repository Structure + Context/Memory + Frontend Modularization (T12.1–T12.5)
  - 2026-03-07 07:18
  - State: Verified
  - Location: `.gitignore`, `data/retrieval/.gitkeep`, `backend/workflow/nodes/llm_worker_node.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/api/main.py`, `backend/api/schemas.py`, `tests/unit/test_nodes.py`, `tests/unit/test_context_builder_retrieval.py`, `tests/unit/test_api_memory_search.py`, `frontend/src/App.jsx`, `frontend/src/state/useChatState.js`, `frontend/src/styles/theme.js`, `frontend/src/utils/renderHelpers.jsx`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`; `npm --prefix frontend run build`; `docker compose config`
  - Notes:
    - Housekeeping: T12.4
    - Backend: T12.1/T12.2/T12.3
    - Frontend: T12.5.

- Capability: Milestone 11 — Usability + Execution Depth (T11.1–T11.5)
  - 2026-03-06 09:03
  - State: Verified
  - Location: `backend/api/main.py`, `backend/api/schemas.py`, `backend/controller/controller_service.py`, `backend/config/settings.py`, `backend/search/budget.py`, `backend/tools/file_tools.py`, `backend/workflow/plan_compiler.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/workflow/nodes/llm_worker_node.py`, `frontend/src/App.jsx`, `frontend/src/api/taskClient.js`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_api_budget.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_api_health_detailed.py`, `tests/unit/test_api_workflow_telemetry.py`, `tests/unit/test_api_streaming.py`, `tests/unit/test_api_file_upload.py`, `tests/unit/test_search_tools.py`, `tests/unit/test_plan_compiler.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_budget.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_workflow_telemetry.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_search_tools.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_health_detailed.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_settings.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_streaming.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_file_upload.py -q`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_plan_compiler.py tests/unit/test_controller_service_integration.py -q`; `npm --prefix frontend run build`
  - Notes:
    - T11.1 — Backend API + Controller Telemetry Surfaces: monthly budget projection populated on `/budget`, workflow execution order persisted for telemetry reads, and structured search/tool failure metadata projected for UI consumption.
    - T11.2 — Frontend Chat/Render + Status UX: assistant markdown/code rendering improved, model indicator readability tightened, cache status mapping aligned to backend health fields, and search failure details rendered inline in chat.
    - T11.3 — Settings/Budget Self-Service Surface: minimal settings write path added with explicit restart-required signaling, settings panel gained edit/save flow, and daily/monthly budget limits became editable from the UI.
    - T11.4 — Task Execution UX Pipeline: SSE task streaming added with progressive chat updates, compact search/read tool previews rendered in chat, and text/markdown/PDF upload context added through additive task submission flow.
    - T11.5 — Planning and Workflow Depth: constrained multi-turn planning added with deterministic bounded decomposition, capped fan-out, ordered subtask execution, and aggregated final output.

- Capability: Milestone 10 — Final Metrics & Invariant Closure (10.1–10.6)
  - 2026-03-05 06:01
  - State: Verified
  - Location: `tests/integration/test_reproducibility_validation.py`, `tests/integration/test_memory_recall_accuracy.py`, `tests/integration/test_drift_rate_measurement.py`, `tests/integration/test_controller_latency_p95.py`, `tests/agentic/test_task_success_rate.py`, `tests/fixtures/retrieval_benchmark/v1/*`, `backend/config/settings.py`, `backend/api/main.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/llm_worker_node.py`, `backend/models/local_inference.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope integration`; `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope agentic`
  - Notes:
    - 10.1 reproducibility validation (Track A-first)
    - 10.2 memory recall accuracy benchmark + gates
    - 10.3 agentic task success rate + gates (agentic scope)
    - 10.4 segmented drift measurement + fixed-seed variance (enabled via 10.6)
    - 10.5 controller latency p95 validation (with documented skip where artifact missing)
    - 10.6 generation seed wiring (unskips fixed-seed drift test)

- Capability: Milestone 9 — UI Completion (9.0–9.8; 9.9 deferred):
  - 2026-03-04 05:16
  - State: Verified
  - Location: `backend/api/main.py`, `backend/api/schemas.py`, `backend/config/settings.py`, `backend/search/budget.py`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`, `frontend/src/components/WorkflowVisualizer.jsx`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_api_settings.py`, `tests/unit/test_api_budget.py`, `tests/unit/test_api_health_detailed.py`, `tests/unit/test_api_health_ready.py`, `tests/unit/test_api_workflow_telemetry.py`, `tests/unit/test_api_schemas.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`; `npm --prefix frontend run build`
  - Notes:
    - API surface (`/settings`, `/budget`, `/health/ready`, `/health/detailed`, `/workflow/{task_id}`), centralized settings projection, budget helpers (rolling 30-day), detailed-health 30s cache semantics, telemetry offset ordering, and frontend client/WorkflowVisualizer/SettingsPanel/header polling split

- Capability: Milestone 9.0 — UI Completion API surface (9.0.1–9.0.6:)
  - 2026-03-03 12:09
  - State: Verified
  - Location: `backend/api/main.py`, `backend/api/schemas.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_api_settings.py`, `tests/unit/test_api_budget.py`, `tests/unit/test_api_health_detailed.py`, `tests/unit/test_api_health_ready.py`, `tests/unit/test_api_workflow_telemetry.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`; `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api.py tests/unit/test_api_entrypoint.py tests/unit/test_api_schemas.py tests/unit/test_api_workflow_telemetry.py -q`
  - Notes:
    -  `/settings`, `/budget`, `/health/detailed`, `/health/ready`, `/workflow/{task_id}`

- Capability: Milestone 8 Live Provider Execution (8.B) — SearXNG + DDG + Tavily
  - 2026-03-02 05:15
  - State: Verified
  - Location: `backend/search/providers/searxng.py`, `backend/search/providers/ddg.py`, `backend/search/providers/tavily.py`, `backend/search/providers/base.py`, `backend/search/providers/ladder.py`, `backend/tools/search_tools.py`, `backend/workflow/nodes/tool_call_node.py`, `backend/config/search/searxng/settings.yml`, `docker-compose.yml`, `backend/requirements.txt`, `.env`, `.env.example`, `tests/unit/test_search_provider_ladder.py`, `tests/unit/test_search_tools.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`; `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_provider_contracts.py tests\unit\test_search_provider_ladder.py tests\unit\test_search_tools.py -q`; `docker compose up -d --force-recreate searxng backend`; `curl.exe -sS -o NUL -w "HTTP=%{http_code}\n" "http://localhost:8080/search?q=smoke&format=json"`; `docker compose exec -T backend sh -lc "SEARCH_SEARXNG_URL=http://127.0.0.1:9/search python -c \"from backend.workflow.nodes.tool_call_node import ToolCallNode; ctx={'task_id':'smoke-862-ddg','tool_call':{'tool_name':'search_web','payload':{'query':'smoke','top_k':3},'external_call':True,'allow_external':True,'sandbox_roots':['/app']}}; out=ToolCallNode().execute(ctx); r=out.get('tool_result',{}); print('TOOL_OK', out.get('tool_ok')); print('CODE', r.get('code')); print('PROVIDER', r.get('provider')); print('ITEMS', len(r.get('items',[]))); print('PROVIDER_LADDER', r.get('attempted_providers')); print('REASON', r.get('reason'))\""`; `.\backend\.venv\Scripts\python.exe -c "import tempfile; from backend.workflow.nodes.tool_call_node import ToolCallNode; td=tempfile.TemporaryDirectory(); root=td.name; ctx={'tool_call': {'tool_name':'search_web','payload': {'query':'python','top_k':3,'preferred_provider':'tavily'},'allow_external': True,'external_call': False,'sandbox_roots':[root],'task_id':'smoke-8.6.3'}}; out=ToolCallNode().execute(ctx); tr=out.get('tool_result',{}); print('CODE', tr.get('code')); print('REASON', tr.get('reason')); print('PROVIDER', tr.get('provider')); print('PREFERRED', tr.get('preferred_provider')); td.cleanup()"`
  - Notes:
    - Live provider execution validated via manual smoke; unit regression remains offline/deterministic.

- Capability: Task 8.6.1 — Live SearXNG provider execution + Docker smoke path
  - 2026-03-02 02:38
  - State: Verified
  - Location: `backend/search/providers/base.py`, `backend/search/providers/searxng.py`, `backend/search/providers/ladder.py`, `backend/tools/search_tools.py`, `docker-compose.yml`, `backend/config/search/searxng/settings.yml`, `.env`, `.env.example`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_provider_contracts.py tests\unit\test_search_provider_ladder.py tests\unit\test_search_tools.py -q`; `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`; `curl.exe -sS -o NUL -w "HTTP=%{http_code}\n" "http://localhost:8080/search?q=smoke&format=json"`; `docker compose exec -T backend python -c "import os, httpx; url=os.environ['SEARCH_SEARXNG_URL']; r=httpx.get(url, params={'q':'smoke','format':'json'}, timeout=10.0); print('HTTP', r.status_code); j=r.json(); print('HAS_RESULTS', isinstance(j.get('results'), list)); print('RESULT_COUNT', len(j.get('results', [])))"`; `docker compose exec -T backend python -c "from backend.workflow.nodes.tool_call_node import ToolCallNode; ctx={'task_id':'smoke-861','tool_call':{'tool_name':'search_web','payload':{'query':'smoke','top_k':3},'external_call':True,'allow_external':True,'sandbox_roots':['/app']}}; out=ToolCallNode().execute(ctx); r=out.get('tool_result',{}); print('TOOL_OK', out.get('tool_ok')); print('CODE', r.get('code')); print('PROVIDER', r.get('provider')); print('ITEMS', len(r.get('items',[])))"`
  - Notes:
    - Live SearXNG path manually smoke-verified; unit regression remains offline/deterministic.

- Capability: Milestone 8 Search + Policy-Bound Escalation (8.A)
  - 2026-03-01 23:24
  - State: Verified
  - Location: `backend/tools/registry.py`, `backend/tools/executor.py`, `tests/unit/test_tool_executor_external_permission.py`, `backend/search/budget.py`, `backend/search/policy.py`, `tests/unit/test_search_budget.py`, `tests/unit/test_search_policy.py`, `backend/search/providers/base.py`, `backend/search/providers/searxng.py`, `backend/search/providers/ddg.py`, `backend/search/providers/tavily.py`, `backend/search/providers/ladder.py`, `tests/fixtures/search/*`, `tests/unit/test_search_provider_contracts.py`, `tests/unit/test_search_provider_ladder.py`, `backend/search/extract.py`, `backend/search/fetch_models.py`, `tests/fixtures/fetch/*`, `tests/unit/test_fetch_extraction_contracts.py`, `backend/tools/search_tools.py`, `backend/workflow/nodes/tool_call_node.py`, `tests/unit/test_search_tools.py`, `backend/tools/__init__.py`, `backend/search/__init__.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit` (PASS excerpts: `PASS WITH SKIPS: unit: 208 tests, 1 skipped`, `UNIT=PASS_WITH_SKIPS`; report `reports\\backend_validation_report_20260301_231857.txt`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_tools.py -q` (PASS excerpt: `5 passed in 0.18s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_provider_contracts.py tests\unit\test_search_provider_ladder.py -q` (PASS excerpt: `8 passed in 0.19s`)
  - Notes:
    - EXTERNAL calls are deny-by-default unless `allow_external=True`
    - budget ledger at `data/search/budget.json` drives deterministic policy decisions (`permission_denied`, `budget_exceeded`, `ok`, `validation_error`)
    - provider and fetch/extract paths are offline fixture-driven (no live HTTP/DNS) with deterministic outputs
    - `search_web`/`fetch_url` are EXTERNAL tools with policy-bound outcomes and conditional ToolCallNode registration.

- Capability: Milestone 7 Semantic Retrieval
  - 2026-03-01 11:32
  - State: Verified
  - Location: `backend/memory/semantic_store.py`, `tests/unit/test_semantic_store_persistence.py`, `tests/unit/test_semantic_store_search_text.py`, `backend/config/settings.py`, `.env.example`, `backend/retrieval/retrieval_types.py`, `backend/retrieval/hybrid_retriever.py`, `tests/unit/test_retrieval_types.py`, `tests/unit/test_hybrid_retriever.py`, `backend/memory/episodic_db.py`, `tests/unit/test_episodic_db_search.py`, `backend/workflow/nodes/context_builder_node.py`, `tests/unit/test_context_builder_retrieval.py`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit` (PASS excerpts: `PASS WITH SKIPS: unit: 180 tests, 1 skipped`, `UNIT=PASS_WITH_SKIPS`; report `reports\\backend_validation_report_20260301_112552.txt`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_context_builder_retrieval.py -q` (PASS excerpt: `3 passed in 0.13s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_hybrid_retriever.py -q` (PASS excerpt: `4 passed in 0.06s`)
  - Notes:
    - Task 7.0.1 added deterministic settings robustness via DEBUG normalization to prevent `DEBUG=release` environment collisions from breaking the unit harness.
    - Persisted FAISS index at `data/semantic/index.faiss` with fail-safe load/rebuild from SQLite metadata (`data/semantic/metadata.db`)
    - normalized semantic similarity scoring via `search_text()` converting L2 distance to `1/(1+distance)` in `[0,1]`; episodic keyword search APIs plus idempotent indexes
    - unified retrieval scoring contract (`0..1` relevance/recency to `final_score`) with deterministic ranking; hybrid retriever orchestration across working-state/semantic/episodic with configurable policy in `RetrievalConfig`
    - ContextBuilder deterministic `Retrieved Context` system-message injection (DI-only retriever, fail-safe behavior)

- Capability: Milestone 6 Redis Cache Layer
  - 2026-02-25 15:22
  - State: Verified
  - Location: `backend/cache/redis_client.py`, `tests/unit/test_redis_client.py`, `backend/cache/key_policy.py`, `tests/unit/test_cache_keys.py`, `backend/cache/metrics.py`, `tests/unit/test_cache_metrics.py`, `backend/workflow/nodes/context_builder_node.py`, `tests/unit/test_context_builder_cache.py`, `backend/tools/executor.py`, `tests/unit/test_tool_executor_cache.py`, `backend/cache/settings.py`, `tests/unit/test_cache_settings.py`, `.env.example`, `.env`
  - Validation: `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit` (PASS excerpts: `UNIT: PASS_WITH_SKIPS`, `UNIT=PASS_WITH_SKIPS`; report `reports\\backend_validation_report_20260225_151659.txt`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_cache_settings.py tests\unit\test_context_builder_cache.py tests\unit\test_tool_executor_cache.py -q` (PASS excerpt: `13 passed in 2.36s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit -q -k cache` (PASS excerpt: `24 passed, 130 deselected in 2.64s`)
  - Notes:
    - Fail-safe optional Redis cache layer with deterministic keys/serialization, in-memory cache metrics, context/task-turn and READ_ONLY tool-result caching with settings-based TTLs and CACHE_ENABLED gating.

- Capability: Milestone 5 Privacy & Security Controls (excluding At-Rest Encryption)
  - 2026-02-24 14:31
  - State: Verified
  - Location: `backend/security/redactor.py`, `tests/unit/test_redactor.py`, `backend/security/audit_logger.py`, `tests/unit/test_audit_logger.py`, `backend/security/privacy_wrapper.py`, `tests/unit/test_privacy_wrapper.py`, `backend/tools/executor.py`, `tests/unit/test_tool_executor_privacy.py`, `backend/workflow/nodes/tool_call_node.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor_privacy.py -q` (PASS excerpt: `7 passed in 0.14s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_controller_service_integration.py -q` (PASS excerpt: `8 passed in 1.86s`); `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit` (PASS excerpts: `UNIT: PASS_WITH_SKIPS`, `UNIT=PASS_WITH_SKIPS`; report `reports\\backend_validation_report_20260224_143129.txt`)
  - Notes:
    - Includes v4-parity PII detection/redaction, JSONL security audit logging, deny-by-default external-call privacy gating with explicit wrapper injection/configuration error on missing wrapper, configurable `tool_call.audit_log_path` with hermetic tests, and additive tool I/O privacy metadata (`privacy`, `redacted_result_text`); At-rest encryption remains Deferred.

- Capability: Milestone 4 Tool System + Sandboxed Execution
  - 026-02-23 14:31
  - State: Verified
  - Location: `backend/tools/registry.py`, `backend/tools/sandbox.py`, `backend/tools/file_tools.py`, `backend/tools/executor.py`, `backend/workflow/nodes/tool_call_node.py`, `backend/workflow/__init__.py`, `backend/controller/controller_service.py`, `tests/unit/test_file_tools.py`, `tests/unit/test_tool_executor.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_file_tools.py -q` (PASS excerpt: `16 passed in 0.12s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor.py -q` (PASS excerpt: `8 passed in 0.15s`); `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_controller_service_integration.py -q` (PASS excerpt: `5 passed in 2.06s`); `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit` (PASS excerpts: `UNIT: PASS_WITH_SKIPS`, `UNIT=PASS_WITH_SKIPS`; report `reports\\backend_validation_report_20260223_142522.txt`)
  - Notes:
    - Includes registry/schema export, sandbox controls, Tier 1 file tools, executor plumbing, and controller ToolCallNode runtime wiring.

- Capability: Baseline Determinism Harness (Milestone 3)
  - 2026-02-23 00:20
  - State: Verified
  - Location: `tests/integration/test_replay_baseline.py`, `backend/controller/controller_service.py`
  - Validation: `.\backend\.venv\Scripts\python.exe -m pytest tests\integration\test_replay_baseline.py -q` (PASS excerpts: `1 passed in 95.66s (0:01:35)`; `1 passed in 48.57s`)
  - Notes:
    -  Deliverables: replay baseline harness; controller latency baseline; deterministic artifact comparison for repeated runs.

- Capability: Deterministic DAG executor (ordering + cycle detection)
  - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/workflow/dag_executor.py`, `tests/unit/test_dag_executor.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_dag_executor.py -q`
  - Notes:
    - Resolves execution order and rejects cyclic workflow graphs.

- Capability: Plan-to-workflow graph compiler
  - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/workflow/plan_compiler.py`, `tests/unit/test_plan_compiler.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_plan_compiler.py -q`
  - Notes:
    - Compiles current plan artifact into the runtime workflow graph.

- Capability: FSM and DAG orchestration integration with per-node DAG trace events
  - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/controller/controller_service.py`, `backend/controller/fsm.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_controller_service_integration.py -q`; `./backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
  - Notes:
    - Controller lifecycle transitions execute DAG phases and emit `dag_node_event` records.

- Capability: UI Header status polling and task-context display/clear behavior (UI-4 evidence pass)
  - 2026-02-20 22:27
  - State: Verified
  - Location: `frontend/src/App.jsx`, runtime surface `http://localhost:3001`
  - Validation: `docker stop jarvisv5-backend-1`; `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health` (connection failure while stopped); `docker start jarvisv5-backend-1`; `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health` (`{"status":"ok","service":"JARVISv5-backend"}`); UI observations `HEADER_STATUS_AFTER_STOP=Offline`, `HEADER_STATUS_AFTER_START=Online`, task context `{task_id:"task-9b0869f3f6", final_state:"ARCHIVE"}`, header short id `0869f3f6`, New Chat clears task/state placeholders
  - Notes:
    - Evidence pass recorded behavior only; no source files modified.

- Capability: LLM output normalization: general single-turn stop + trim (no prompt-specific branching)
  - 2026-02-18 15:00
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` (`EXIT:0`), report `reports/backend_validation_report_20260218_145647.txt`
  - Notes:
    - Runtime continuation proof returned `Alice` with `HAS_USERNAME=False` and `HAS_PASSWORD=False`.

- Capability: Deterministic “reply with only the name” recall behavior
  - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`, `tests/unit/test_api_entrypoint.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; runtime `POST /task` continuation sequence with Task B `{"user_input":"What is my name? Reply with only the name."}` returned `llm_output="Alice"`
  - Notes:
    - Verified with same-task continuation and strict equality check.

- Capability: LLM generation constrained to single assistant turn (stop tokens + normalization)
  - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` (`EXIT:0`); report `reports/backend_validation_report_20260218_144702.txt`; runtime check `HAS_USERNAME=False`, `HAS_PASSWORD=False`
  - Notes:
    - Applies stop markers and first-turn trimming before output is persisted.

- Capability: Working-state transcript persisted across turns (bounded)
  - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/memory/working_state.py`, `backend/memory/memory_manager.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/context_builder_node.py`
  - Validation: runtime continuation sequence showed same `task_id` across Task A/Task B and multi-turn transcript retrieval via `GET /task/{task_id}` in prior M12 evidence
  - Notes:
    - Transcript is bounded and reused in prompt history.

- Capability: POST /task continuation via optional task_id
  - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/api/main.py`, `backend/controller/controller_service.py`, `tests/unit/test_api_entrypoint.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; runtime Task A/Task B responses showed same `task_id`
  - Notes:
    - Continuation reuses existing task linkage without adding new endpoints.

- Capability: Backend validation harness: per-test pytest listing
  - 2026-02-18 13:39
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py` (UNIT section lists per-test `✓/✗/○` lines)
  - Notes:
    - Uses pytest `-v` capture with deterministic truncation for long suites.

- Capability: Backend validation harness: standardized report format + invariants
  - 2026-02-18 13:28
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py` produced summary, invariants, final verdict and report file `reports\backend_validation_report_20260218_133955.txt`
  - Notes:
    - Terminal and report now share consistent structured sections.

- Capability: Backend validation harness: docker-inference scope
  - 2026-02-18 13:29
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` with `EXIT:0`; report `reports\backend_validation_report_20260218_132908.txt`
  - Notes:
    - Non-executed unit/integration/agentic suites remain `SKIP` in summary/invariants.

- Capability: Host-Venv Backend Validation Fallback for Missing llama_cpp (M6)
  - 2026-02-18 11:46
  - State: Verified
  - Location: `tests/unit/test_nodes.py`, `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_nodes.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py`
  - Notes:
    - Node test now records clean import failure path; rc=5 in empty suites is WARN.

- Capability: Model Auto-Fetch on Missing Selected GGUF (M1)
  - 2026-02-18 10:54
  - State: Verified
  - Location: `backend/models/model_registry.py`, `backend/controller/controller_service.py`, `models/models.yaml`, `.env.example`, `tests/unit/test_model_registry.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_model_registry.py -q`; runtime logs in `reports/m1_uvicorn_20260218_105417.log` and `reports/m1_uvicorn_20260218_105417.err`
  - Notes:
    - Missing model downloaded once when enabled and reused on subsequent call.

- Capability: Docker Backend Real llama_cpp Inference via /task (M2)
  - 2026-02-18 11:02
  - State: Verified
  - Location: `docker-compose.yml`, `backend/Dockerfile`, `backend/workflow/nodes/llm_worker_node.py`, `backend/controller/controller_service.py`
  - Validation: `docker compose config`; `docker compose build backend`; `docker compose up -d redis backend`; `docker compose exec -T backend python -c "import llama_cpp; print('OK')"`; `GET /health`; `POST /task` non-empty `llm_output`
  - Notes:
    - Backend container imported llama_cpp and returned non-empty task output.

- Capability: Docker Runtime Environment (Layer 0)
  - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/Dockerfile`
  - Validation: `docker compose build backend` success.
  - Notes:
    - Multi-stage build compiles llama.cpp and llama-cpp-python from source.

- Capability: Workflow Nodes (Router, LLM, Validator)
  - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/workflow/nodes/`
  - Validation: `pytest tests/unit/test_nodes.py`
  - Notes:
    - Stateless processing nodes for specific roles.

- Capability: API Entry Point (/task)
  - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/api/main.py`
  - Validation: `curl http://localhost:8000/task`
  - Notes:
    - POST endpoint calls ControllerService; GET retrieves state.

## Observed Initial Inventory

- Capability: Controller Node-Orchestrated Run Path - 2026-02-16 07:55
  - State: Verified
  - Location: `backend/controller/controller_service.py`
  - Validation: `docker compose run backend python -m pytest tests/unit/test_controller_service_integration.py -v`
  - Notes: Deterministic FSM invokes workflow nodes and degrades to FAILED on node errors.

- Capability: Workflow Node Layer (Router/Context/LLM/Validator) - 2026-02-16 07:11
  - State: Verified
  - Location: `backend/workflow/nodes/base_node.py`, `backend/workflow/nodes/router_node.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/workflow/nodes/llm_worker_node.py`, `backend/workflow/nodes/validator_node.py`, `backend/workflow/__init__.py`, `tests/unit/test_nodes.py`
  - Validation: `docker compose run backend python -m pytest tests/unit/test_nodes.py -v`
  - Notes: LLM node attempts real llama_cpp import and handles missing model gracefully.

- Capability: Backend Source Bind Mount for Runtime Sync - 2026-02-16 07:31
  - State: Verified
  - Location: `docker-compose.yml`
  - Validation: `docker compose run backend python -m pytest tests/unit/test_nodes.py -v`
  - Notes: Backend mounts `./:/app` while retaining `./data:/app/data` and `./models:/app/models`.

- Capability: Dockerized Backend Runtime (Layer 0) - 2026-02-16 05:17
  - State: Implemented
  - Location: `backend/Dockerfile`, `docker-compose.yml`
  - Validation: `docker compose build backend` + `curl http://localhost:8000/health`
  - Notes: Multi-stage build compiles `llama.cpp` from source; Python 3.12 runtime.

- Capability: Finite State Machine (FSM) - 2026-02-15 07:41
  - State: Implemented
  - Location: `backend/controller/fsm.py`
  - Validation: `pytest tests/unit/test_controller_fsm.py`
  - Notes: Defines INIT, PLAN, EXECUTE, VALIDATE, COMMIT, ARCHIVE, FAILED states.

- Capability: Deterministic Controller Service - 2026-02-15 07:41
  - State: Implemented
  - Location: `backend/controller/controller_service.py`
  - Validation: `pytest tests/unit/test_controller_service.py`
  - Notes: Orchestrates tasks through FSM and integrates with MemoryManager.

- Capability: Episodic Trace (SQLite) - 2026-02-14 18:13
  - State: Implemented
  - Location: `backend/memory/episodic_db.py`
  - Validation: `pytest tests/unit/test_episodic_db.py`
  - Notes: Append-only log of decisions, tool calls, and validations.

- Capability: Working State (JSON) - 2026-02-14 18:13
  - State: Implemented
  - Location: `backend/memory/working_state.py`
  - Validation: `pytest tests/unit/test_working_state.py`
  - Notes: Ephemeral task state managed via JSON files.

- Capability: Semantic Memory (Vector Store) - 2026-02-14 18:13
  - State: Implemented
  - Location: `backend/memory/semantic_store.py`
  - Validation: `pytest tests/unit/test_semantic_store.py`
  - Notes: FAISS index + SQLite metadata; uses all-MiniLM-L6-v2.

- Capability: Unified Memory Manager - 2026-02-14 18:13
  - State: Implemented
  - Location: `backend/memory/memory_manager.py`
  - Validation: `pytest tests/unit/test_memory_manager.py`
  - Notes: Single interface for all memory layers.

- Capability: Dockerized Backend Service - 2026-02-14 13:35
  - State: Implemented
  - Location: `docker-compose.yml`, `backend/Dockerfile`
  - Validation: `docker compose up -d` + `curl http://localhost:8000/health`
  - Notes: Python 3.12, FastAPI, Uvicorn.

- Capability: Dockerized Frontend Service - 2026-02-14 13:35
  - State: Implemented
  - Location: `docker-compose.yml`, `frontend/Dockerfile`
  - Validation: `docker compose build frontend`
  - Notes: Node 18, Vite, React.

- Capability: Configuration Management - 2026-02-14 13:35
  - State: Implemented
  - Location: `backend/config/settings.py`
  - Validation: `backend/.venv/Scripts/python -c "from backend.config.settings import Settings..."`
  - Notes: Pydantic-based, loads from .env.

- Capability: API Health Check - 2026-02-14 13:35
  - State: Implemented
  - Location: `backend/api/main.py`
  - Validation: `GET /health returns 200 OK.`
  - Notes: CORS enabled for dev.

## Appendix