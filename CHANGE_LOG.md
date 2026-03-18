# CHANGE_LOG.md
> :
> No edits/reorders/deletes of past entries. If an entry is wrong, append a corrective entry.

## Rules
- Write an entry only after task objective is “done” and supported by evidence.
- **Ordering:** Entries are maintained in **descending chronological order** (newest first, oldest last).
- **Append location:** New entries must be added **at the top of the Entries section**, directly under `## Entries`.
- Each entry must include:
  - Timestamp: `YYYY-MM-DD HH:MM`
  - Summary: 1–2 lines, past tense
  - Scope: files/areas touched
  - Evidence: exact command(s) run + a minimal excerpt pointer (or embedded excerpt ≤10 lines)
- If a change is reverted, append a new entry describing the revert and why.

## Entries

- 2026-03-18 08:27
  - Summary: Completed bugfix-01 by fixing controller planned aggregation for upload-driven execution so redundant repeated subtask outputs no longer persisted as duplicated `[Part N]` blocks.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Notes:
    - Upload-driven planned aggregation now collapses repeated identical subtask outputs.
    - When deduped to a single upload result, assistant output is persisted without `[Part N]` wrappers.
    - Distinct planned subtasks still aggregate normally into multi-part output.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `35 passed in 49.94s`
    - `backend\\.venv\\Scripts\\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `unit: 368 tests, 1 skipped`

- 2026-03-18 07:07
  - Summary: Completed bugfix-04 semantic-memory population slice by writing semantic memory from the successful validated controller path only, with fail-safe persistence behavior.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Notes:
    - Semantic writes now occur only after validation passes and use final assistant output metadata (`task_id`, `source=assistant_final`, `intent`, `final_state_hint=validated`).
    - Writes are skipped for invalid flows and empty/trivially low-value outputs; retrieval/UI follow-up remains a separate task if needed.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `34 passed in 51.65s`
    - `backend\\.venv\\Scripts\\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-03-17 06:40
  - Summary: bugfix-04 - Completed a configuration/runtime-only fix for the cache connectivity issue by correcting `REDIS_URL` to the Docker service address (`redis://redis:6379/0`) and recreating the backend container so runtime settings reloaded correctly.
  - Scope: `.env`, `.env.example`, backend container runtime refresh (no rebuild)
  - Evidence:
    - `curl -sS http://localhost:8000/health/detailed`
      - PASS excerpt: `"cache":{"enabled":true,"connected":true}`
    - `docker compose exec -T backend python -c "from backend.config.settings import Settings; print(Settings().REDIS_URL)"`
      - PASS excerpt: `redis://redis:6379/0`

- 2026-03-17 14:55
  - Summary: Completed bugfix-05 as a minimal settings-surface enhancement: `/settings` now exposes selectable `ollama_model_options`, and the Settings UI now uses a dropdown/select for Ollama model choice. `ollama_base_url` remained read-only (not editable via settings write path) and restart-required semantics remained unchanged.
  - Scope: `backend/api/schemas.py`, `backend/api/main.py`, `backend/config/settings.py`, `frontend/src/components/SettingsPanel.jsx`, `tests/unit/test_api_settings.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_config.py`.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests/unit/test_api_settings.py tests/unit/test_api_schemas.py tests/unit/test_config.py -q`
      - PASS excerpt: `32 passed in 1.29s`
    - `backend\\.venv\\Scripts\\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 686ms`

- 2026-03-17 14:16
  - Summary: Completed bugfix-02 as a frontend UI composition/visibility fix by removing inline Workflow Telemetry rendering from the response/message frame and making telemetry available only through an explicit toggle/flyout panel.
  - Scope: `frontend/src/App.jsx`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 677ms`

- 2026-03-17 13:57
  - Summary: Completed bugfix-06 as a frontend display-layer settings snapshot fix by correcting `searxng_url` label casing to `SearXNG URL` and remapping internal Docker endpoint display (`searxng:8080`) to user-facing `localhost:8888` for display only.
  - Scope: `frontend/src/components/SettingsPanel.jsx`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 1.06s`

- 2026-03-15 13:13 — User adjusted frontend host port re-align to 3001
  - Summary: Completed a configuration/documentation-only change by updating the JARVISv5 frontend host-facing port from `3000` to `3001` (`3001:3000`) and aligning local access documentation to `http://localhost:3001`.
- Scope: `docker-compose.yml`, docs referencing local frontend URL
- Evidence: Compose frontend port mapping: `3001:3000`, Local documentation URL: `http://localhost:3001`
 
- 2026-03-15 04:51
  - Summary: Completed a documentation-only `Project.md` reality-alignment pass to keep it vision/intent-focused by strengthening long-term voice direction language, removing active encryption-at-rest and model-integrity implementation phrasing, and softening selected repository/interface wording.
  - Scope: `Project.md`.
  - Evidence:
    - `git status --porcelain`
      - PASS excerpt: `M Project.md`

- 2026-03-14 21:33
  - Summary: Completed T16.2.7 by adding the minimum residual Ollama backend test coverage: explicit cloud-registry exclusion assertion, deterministic timeout-to-unreachable provider mapping, and controller fall-through coverage when Ollama is enabled with blank model.
  - Scope: `tests/unit/test_escalation_providers.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `48 passed in 6.28s`
    - `backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 365 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`

- 2026-03-14 21:25
  - Summary: Completed T16.2.6 by adding a dedicated Ollama Escalation subsection in SettingsPanel with editable `allow_ollama_escalation` and `ollama_model` controls, plus read-only `ollama_base_url` display with restart-required note.
  - Scope: `frontend/src/components/SettingsPanel.jsx`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 1.22s`

- 2026-03-14 21:09
  - Summary: Completed T16.2.4 by inserting an Ollama pre-check fallback attempt in local-model-unavailable handling so controller fallback order is local model -> Ollama (when enabled/configured) -> existing cloud escalation path.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `31 passed in 5.96s`

- 2026-03-14 21:04
  - Summary: Completed T16.2.3 by adding an Ollama escalation provider with execution-time settings lookup and deterministic offline-tested failure handling for missing model and unreachable host paths.
  - Scope: `backend/models/providers/ollama_provider.py`, `backend/models/providers/__init__.py`, `tests/unit/test_escalation_providers.py`.
  - Evidence:
    - `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py -q`
      - PASS excerpt: `14 passed in 0.86s`

- 2026-03-14 20:57
  - Summary: Completed T16.2.2 by adding Linux-compatible backend host-gateway mapping for `host.docker.internal` in compose, with no other compose/service behavior changes.
  - Scope: `docker-compose.yml`.
  - Evidence:
    - `docker compose config`
      - PASS excerpt: `extra_hosts:`
      - PASS excerpt: `- host.docker.internal=host-gateway`

- 2026-03-14 20:55
  - Summary: Completed T16.2.1 by adding Ollama escalation settings defaults, safe projection fields, editable-settings constraints, and `.env`/`.env.example` key alignment with focused config/settings API coverage.
  - Scope: `backend/config/settings.py`, `backend/api/schemas.py`, `backend/api/main.py`, `.env.example`, `.env`, `tests/unit/test_config.py`, `tests/unit/test_api_settings.py`.
  - Evidence:
    - `backend\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py tests/unit/test_api_settings.py -q`
      - PASS excerpt: `27 passed in 1.42s`

- 2026-03-14 19:24
  - Summary: Completed a separate T16.4 corrective gap-closure pass by adding the remaining roadmap-required test coverage for strict provider registration and Anthropic registry dispatch integration.
  - Scope: `tests/unit/test_escalation_providers.py`, `tests/unit/test_controller_service_integration.py` (test-only corrective work).
  - Notes:
    - Added `test_all_providers_registered` and additive controller integration coverage for dispatch to a registered Anthropic provider.
  - Evidence:
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `39 passed in 10.31s`
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `350 passed, 1 skipped in 89.80s (0:01:29)`

- 2026-03-13 15:10
  - Summary: Completed T16.4 as a verification-only closeout for M16 escalation-provider/controller coverage with no additional implementation changes required.
  - Scope: Verification-only task; no production or test file modifications required beyond existing T16 work.
  - Notes:
    - Confirmed focused provider/controller coverage and full unit regression pass without introducing new file changes for T16.4.
  - Evidence:
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `37 passed in 5.47s`
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `348 passed, 1 skipped in 44.15s`

- 2026-03-13 15:02
  - Summary: Completed T16.3 by populating the controller escalation dispatch registry with real provider instances while preserving existing policy-gated escalation decision flow.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Notes:
    - Added focused controller integration coverage asserting registry population and provider-base dispatch-table shape.
  - Evidence:
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `27 passed in 5.50s`
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `348 passed, 1 skipped in 44.12s`

- 2026-03-13 14:00
  - Summary: Completed T16.2.a corrective pass by replacing deprecated Gemini SDK dependency (`google-generativeai`) with supported `google-genai`, updating `GeminiEscalationProvider` to supported SDK usage, and updating only Gemini-focused provider tests.
  - Scope: `backend/requirements.txt`, `backend/models/providers/gemini_provider.py`, `tests/unit/test_escalation_providers.py`.
  - Notes:
    - Prior `google.generativeai` deprecation warning is gone in focused provider test execution.
  - Evidence:
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py -q`
      - PASS excerpt: `10 passed in 0.81s`
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `347 passed, 1 skipped in 49.28s`

- 2026-03-13 13:32
  - Summary: Completed T16.2 by adding concrete escalation provider implementations for Anthropic, OpenAI, Gemini, and Grok using the existing escalation provider contract, with provider package exports and execute-time API key lookup through `ApiKeyRegistry`.
  - Scope: `backend/models/providers/__init__.py`, `backend/models/providers/anthropic_provider.py`, `backend/models/providers/openai_provider.py`, `backend/models/providers/gemini_provider.py`, `backend/models/providers/grok_provider.py`, `tests/unit/test_escalation_providers.py`.
  - Evidence:
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_providers.py -q`
      - PASS excerpt: `10 passed, 1 warning in 3.96s`
    - `e:\WORK\CODE\GitHub\bentman\Repositories\JARVISv5\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `347 passed, 1 skipped, 1 warning in 61.92s`

- 2026-03-12 19:38
  - Summary: Completed T16.1 by adding provider SDK dependencies for Anthropic, Gemini, and Groq under the existing LLM/AI dependency section while preserving the existing OpenAI dependency line unchanged.
  - Scope: `backend/requirements.txt`.
  - Evidence:
    - `backend/.venv/Scripts/pip install -r backend/requirements.txt`
      - PASS excerpt: `Successfully installed anthropic-0.84.0 ... google-generativeai-0.8.6 ... groq-1.1.1`
    - `backend/.venv/Scripts/python -c "import anthropic, google.generativeai, groq, openai; print('ok')"`
      - PASS excerpt: `ok`

- 2026-03-12 13:35
  - Summary: Completed T15.7 with additive test-only M15 acceptance coverage by adding controller escalation deny-path tests (empty provider, provider key missing, zero budget) and explicit `/settings` API-key non-leakage assertions.
  - Scope: `tests/unit/test_controller_service_integration.py`, `tests/unit/test_api_settings.py`.
  - Notes:
    - Test-only scope; no production file changes.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py tests/unit/test_api_settings.py -q`
      - PASS excerpt: `36 passed in 4.83s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `337 passed, 1 skipped in 42.27s`

- 2026-03-12 13:18
  - Summary: Added a separate corrective frontend entry to fix the SettingsPanel first-load dirty-state root cause so the editable settings section initializes/rendered normally instead of entering a budget-only panel state.
  - Scope: `frontend/src/components/SettingsPanel.jsx`.
  - Notes:
    - Corrected null/null equality semantics for both editable settings and budget draft comparisons, preserving existing save/cancel, dirty-state, restart-notice, escalation controls, and no backend changes.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `vite v5.4.21 building for production...`
      - PASS excerpt: `✓ 199 modules transformed.`
      - PASS excerpt: `✓ built in 678ms`

- 2026-03-12 12:26
  - Summary: Completed T15.6 by adding escalation controls to `SettingsPanel.jsx`, sourcing escalation provider dropdown options from backend `escalation_configured_providers`, handling empty configured-provider state with disabled dropdown + helper text while preserving current draft value, and showing `escalation_budget_usd` as read-only.
  - Scope: `frontend/src/components/SettingsPanel.jsx`.
  - Notes:
    - `frontend/src/api/taskClient.js` remained unchanged for this task.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 199 modules transformed.`
      - PASS excerpt: `✓ built in 984ms`

- 2026-03-12 12:13
  - Summary: Added a separate corrective backend escalation-settings contract pass that aligns roadmap behavior before frontend T15.6 work: safe `/settings` projection now includes `escalation_configured_providers`, `ESCALATION_BUDGET_USD` remains visible in `GET /settings` but is read-only via API, and `POST /settings` escalation writes are limited to `allow_model_escalation` and `escalation_provider`.
  - Scope: `backend/config/settings.py`, `backend/api/schemas.py`, `backend/api/main.py`, `tests/unit/test_config.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_api_settings.py`.
  - Notes:
    - This corrective contract pass unblocked T15.6 frontend provider-selection implementation.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py tests/unit/test_api_schemas.py tests/unit/test_api_settings.py -q`
      - PASS excerpt: `26 passed in 0.64s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `333 passed, 1 skipped in 41.04s`

- 2026-03-12 11:27
  - Summary: Completed T15.5 by finishing the live `/settings` API escalation-field response surface so `GET /settings` and `POST /settings` return projection-backed `allow_model_escalation`, `escalation_provider`, and `escalation_budget_usd`, with focused settings API assertion updates and no schema/settings-model expansion in this task.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_settings.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_settings.py -q`
      - PASS excerpt: `8 passed in 0.55s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `330 passed, 1 skipped in 42.42s`

- 2026-03-12 10:27
  - Summary: Completed T15.4 by integrating controller escalation handling at local-model failure points with policy/settings decisioning, API-key-registry key-presence derivation, controller-local escalation provider registry dispatch, strict outbound prompt redaction before escalated provider execution, and additive escalation status/code/reason/error context fields while preserving non-escalation behavior outside local-model-failure paths.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `23 passed in 4.21s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `330 passed, 1 skipped in 42.58s`

- 2026-03-12 10:13
  - Summary: Completed T15.3 by adding escalation typed settings, escalation provider normalization/validation aligned to provider registry, escalation safe-projection/editable-settings wiring, escalation schema support for settings read/write, and `.env`/`.env.example` parity with focused config/schema/settings test coverage.
  - Scope: `backend/config/settings.py`, `backend/api/schemas.py`, `.env`, `.env.example`, `tests/unit/test_config.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_api_settings.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_config.py tests/unit/test_api_schemas.py tests/unit/test_api_settings.py -q`
      - PASS excerpt: `23 passed in 0.59s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `326 passed, 1 skipped in 43.49s`

- 2026-03-12 09:59
  - Summary: Completed T15.2 by introducing the escalation policy module/public contract, centralizing escalation decision codes/paths/reasons, wiring configured-provider awareness through `ApiKeyRegistry`, and adding deterministic stub escalation provider plus focused escalation-policy tests.
  - Scope: `backend/models/escalation_policy.py`, `backend/models/__init__.py`, `tests/unit/test_escalation_policy.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_escalation_policy.py -q`
      - PASS excerpt: `9 passed in 0.12s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `318 passed, 1 skipped in 42.42s`

- 2026-03-12 09:41
  - Summary: Completed T15.1 by adding `.env`/`.env.example` parity for cloud-model provider API keys, introducing a centralized read-only API key registry with canonical supported-provider set, and adding focused API-key unit coverage with full unit regression validation.
  - Scope: `.env`, `.env.example`, `backend/config/api_keys.py`, `tests/unit/test_api_keys.py`.
  - Notes:
    - Preserved existing `TAVILY_API_KEY` entry and value in `.env` unchanged.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_keys.py -q`
      - PASS excerpt: `5 passed in 0.04s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `309 passed, 1 skipped in 60.89s (0:01:00)`

- 2026-03-12 07:35
  - Summary: Added a separate M14 acceptance-gap corrective test-only pass by adding additive controller integration acceptance tests for research/chat/explicit-tool-call routing and additive explicit `GET /settings` search projection assertions for `allow_paid_search`, `searxng_url`, and `tavily_key_configured`.
  - Scope: `tests/unit/test_controller_service_integration.py`, `tests/unit/test_api_settings.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `19 passed in 3.60s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_settings.py -q`
      - PASS excerpt: `7 passed in 0.53s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `304 passed, 1 skipped in 39.89s`

- 2026-03-12 06:58
  - Summary: Completed T14.6 by adding additive M14 consolidation test coverage only, including explicit `SearchWebNode` policy-denied behavior assertions and explicit `code` intent graph-preservation assertions in controller integration tests.
  - Scope: `tests/unit/test_search_web_node.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `300 passed, 1 skipped in 40.08s`

- 2026-03-12 06:46
  - Summary: Completed T14.5 by cleaning up controller research routing: removed research auto-injected `tool_call` runtime payload wiring, routed research intent through `SearchWebNode` graph insertion, and preserved explicit `tool_call` precedence plus existing chat/code paths.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `298 passed, 1 skipped in 39.51s`

- 2026-03-12 06:36
  - Summary: Completed T14.4 by adding a dedicated `SearchWebNode` with typed `Settings()` runtime controls, in-node provider ladder construction, and tier-policy-based allow/deny flow while preserving roadmap boundary (no ToolCallNode/search_tools routing).
  - Scope: `backend/workflow/nodes/search_web_node.py`, `backend/workflow/__init__.py`, `tests/unit/test_search_web_node.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_search_web_node.py tests/unit -q`
      - PASS excerpt: `297 passed, 1 skipped in 63.28s (0:01:03)`

- 2026-03-12 06:17
  - Summary: Completed T14.3 by replacing binary external-search policy with deterministic three-path tier enforcement (`blocked` / `free` / `paid`), adding tier-aware policy request fields, and applying typed-settings fallback for paid controls while preserving existing policy call style compatibility.
  - Scope: `backend/search/policy.py`, `tests/unit/test_search_policy.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `292 passed, 1 skipped in 50.64s`

- 2026-03-12 06:01
  - Summary: Completed T14.2 by wiring typed settings for search fields (`ALLOW_PAID_SEARCH`, `SEARCH_SEARXNG_URL`, `TAVILY_API_KEY`), adding safe `/settings` projection fields (`allow_paid_search`, `searxng_url`, `tavily_key_configured`), removing provider-local `os.getenv(...)` usage in SearXNG/Tavily providers, and syncing `.env.example`.
  - Scope: `backend/config/settings.py`, `backend/api/main.py`, `backend/api/schemas.py`, `backend/search/providers/searxng.py`, `backend/search/providers/tavily.py`, `.env.example`, `tests/unit/test_api_settings.py`, `tests/unit/test_config.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `286 passed, 1 skipped in 47.90s`

- 2026-03-12 05:34
  - Summary: Completed T14.1 by adding additive provider tier metadata for search providers and explicit local/external + free/paid classification for SearXNG, DuckDuckGo, and Tavily, while preserving existing provider execution behavior and ladder order/fallback.
  - Scope: `backend/search/providers/base.py`, `backend/search/providers/searxng.py`, `backend/search/providers/ddg.py`, `backend/search/providers/tavily.py`, `tests/unit/test_search_provider_contracts.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit -q`
      - PASS excerpt: `284 passed, 1 skipped in 66.05s (0:01:06)`

- 2026-03-07 08:57
  - Summary: Completed T13.4 by adding a header-accessible frontend Memory Search panel with query/results flow, source/snippet/timestamp rendering, and minimal result-to-chat reference insertion while keeping panel open/close behavior isolated from chat state.
  - Scope: `frontend/src/components/MemoryPanel.jsx`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 709ms`

- 2026-03-07 08:47
  - Summary: Completed T13.3 by replacing shallow presence-only validation with deterministic quality-depth gates, emitting explicit validation artifacts (`validation_errors`, `validation_status`, `is_valid`), and preserving controller fail-closed behavior on validation failure.
  - Scope: `backend/workflow/nodes/validator_node.py`, `tests/unit/test_nodes.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`
      - PASS excerpt: `283 passed, 1 skipped in 51.34s`

- 2026-03-07 07:57
  - Summary: Completed T13.2 by adding deterministic `research` intent routing with explicit keyword rules, preserving `code` precedence and `chat` fallback, and routing research requests through existing tool-call execution via controller-side auto-injection.
  - Scope: `backend/workflow/nodes/router_node.py`, `backend/controller/controller_service.py`, `tests/unit/test_nodes.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`
      - PASS excerpt: `278 passed, 1 skipped in 72.57s (0:01:12)`

- 2026-03-07 07:14
  - Summary: Completed T12.5 frontend structure refactor by extracting chat state/handlers into `state/useChatState.js`, extracting theme/style constants into `styles/theme.js`, extracting render/preview helpers into `utils/renderHelpers.jsx`, and reducing `App.jsx` to a thin composition shell.
  - Scope: `frontend/src/App.jsx`, `frontend/src/state/useChatState.js`, `frontend/src/styles/theme.js`, `frontend/src/utils/renderHelpers.jsx`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 690ms`
    - `find /c /v "" < frontend\src\App.jsx`
      - PASS excerpt: `App.jsx` line count `131`

- 2026-03-07 07:03
  - Summary: Completed T12.3 by adding additive `GET /memory/search` with semantic and episodic result projection, explicit empty-query validation, and deterministic zero-results behavior.
  - Scope: `backend/api/main.py`, `backend/api/schemas.py`, `tests/unit/test_api_memory_search.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`
      - PASS excerpt: `272 passed, 1 skipped in 40.89s`

- 2026-03-07 06:51
  - Summary: Completed T12.2 by adding retrieval-context token budget enforcement during context-message assembly with deterministic first-fit prefix trimming while preserving retrieval/ranking behavior.
  - Scope: `backend/workflow/nodes/context_builder_node.py`, `tests/unit/test_context_builder_retrieval.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`
      - PASS excerpt: `269 passed, 1 skipped in 41.11s`

- 2026-03-07 06:27
  - Summary: Completed T12.1 by wiring `context["messages"]` into LLM prompt construction when present, while preserving single-turn fallback and existing seed/stop/normalization/stream-chunk behavior.
  - Scope: `backend/workflow/nodes/llm_worker_node.py`, `tests/unit/test_nodes.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/ -q`
      - PASS excerpt: `266 passed, 1 skipped in 41.13s`

- 2026-03-07 06:07
  - Summary: Completed T12.4 repo layout cleanup by adding retrieval placeholder tracking, updating data ignore allowlist for retrieval placeholder, removing legacy `backend/Dockerfile.v4`, and re-validating compose and reference state.
  - Scope: `data/retrieval/.gitkeep`, `.gitignore`, `backend/Dockerfile.v4`.
  - Evidence:
    - `if exist data\retrieval\.gitkeep (echo retrieval_gitkeep_PRESENT) else (echo retrieval_gitkeep_MISSING)`
      - PASS excerpt: `retrieval_gitkeep_PRESENT`
    - `if exist backend\Dockerfile.v4 (echo backend_Dockerfile_v4_STILL_PRESENT) else (echo backend_Dockerfile_v4_REMOVED)`
      - PASS excerpt: `backend_Dockerfile_v4_REMOVED`
    - `docker compose config >NUL && echo docker_compose_config_PASS || echo docker_compose_config_FAIL`
      - PASS excerpt: `docker_compose_config_PASS`
    - `git grep -n "Dockerfile.v4"`
      - PASS excerpt: matches present only in `roadmap-20260306.md` documentation references.

- 2026-03-06 09:03
  - Summary: Completed Milestone 11 / Sub-Task T11.5.1 by adding a constrained multi-turn planning MVP with deterministic bounded decomposition, capped fan-out, and controller-side planned aggregation while preserving linear flow fallback.
  - Scope: `backend/workflow/plan_compiler.py`, `backend/controller/controller_service.py`, `tests/unit/test_plan_compiler.py`, `tests/unit/test_controller_service_integration.py`.
  - Key behaviors:
    - Added deterministic constrained plan shape with explicit mode (`linear`/`planned`), ordered subtask list, and max-subtask cap.
    - Added bounded decomposition trigger for complex prompts with deterministic ordering and hard fan-out cap (`MAX_SUBTASKS=3`).
    - Added controller planned execution loop for ordered subtask execution and deterministic aggregated final output (`[Part N]` sections).
    - Preserved existing linear execution path when planning trigger conditions are not met.
    - Added focused unit/integration coverage for planner trigger/order/cap and planned aggregation + linear fallback behavior.
  - Evidence:
    - `.\backend\.venv\Scripts\python -m pytest tests/unit/test_plan_compiler.py tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `14 passed in 2.33s`

- 2026-03-06 08:38
  - Summary: Completed Milestone 11 / Sub-Task T11.4.3 by adding additive multipart task upload support (`POST /task/upload`) for text/PDF-first context ingestion while preserving existing JSON `POST /task` behavior.
  - Scope: `backend/api/main.py`, `backend/tools/file_tools.py`, `backend/workflow/nodes/context_builder_node.py`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`, `tests/unit/test_api_file_upload.py`.
  - Key behaviors:
    - Added `POST /task/upload` multipart path with deterministic request parsing and fail-closed handling.
    - Added bounded extraction for in-scope upload types only: `.txt`, `.md`, `.pdf`.
    - Added deterministic unsupported-file handling (`415`, `unsupported_file_type`) and extraction-failure handling (`422`, `file_extraction_failed`).
    - Added attachment metadata projection including roadmap-aligned fields: `filename`, `mime_type`, `extracted_text_length` (plus minimal additive fields).
    - Added frontend composer file picker and upload submit path while preserving existing JSON/streaming submit behavior when no file is selected.
    - Added focused backend upload tests for txt/md success, unsupported extension rejection, and JSON backward compatibility.
  - Evidence:
    - `.\backend\.venv\Scripts\python -m pytest tests/unit/test_api_file_upload.py -q`
      - PASS excerpt: `4 passed in 27.45s`

- 2026-03-06 08:12
  - Summary: Completed Milestone 11 / Sub-Task T11.4.2 by adding compact tool result previews in chat with additive `tool_preview` projection in SSE `done` payload and frontend rendering support for baseline `search` and `read` tool outputs.
  - Scope: `backend/api/main.py`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`.
  - Key behaviors:
    - Added additive `tool_preview` projection on streaming `POST /task/stream` terminal `done` payload.
    - Added compact preview rendering path for `search` and `read` tool names only.
    - Enforced bounded preview display (up to 3 items with overflow line) and graceful degradation when metadata is partial/missing.
    - Preserved existing assistant markdown rendering and existing failure rendering behavior.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 653ms`

- 2026-03-06 07:29
  - Summary: Completed Milestone 11 / Sub-Task T11.4.1 by adding additive SSE task transport (`POST /task/stream`) with deterministic first-pass `chunk` → `done` emission, frontend progressive chat rendering support, and focused streaming contract tests.
  - Scope: `backend/api/main.py`, `backend/workflow/nodes/llm_worker_node.py`, `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`, `tests/unit/test_api_streaming.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_api_streaming.py -q`
      - PASS excerpt: `3 passed in 26.44s`
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ built in 667ms`

- 2026-03-06 07:03
  - Summary: Completed Milestone 11 / Sub-Task T11.3.3 by adding budget management basics for `daily_limit_usd` and `monthly_limit_usd`, including backend write path and settings panel budget edit/save flow with immediate apply behavior (no restart required).
  - Scope: `backend/api/main.py`, `backend/search/budget.py`, `frontend/src/components/SettingsPanel.jsx`, `frontend/src/api/taskClient.js`, `tests/unit/test_api_budget.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_budget.py -q`
      - PASS excerpt: `7 passed in 0.57s`

- 2026-03-06 06:29
  - Summary: Completed Milestone 11 / Sub-Task T11.3.2 by adding settings panel edit/save flow for the approved fields with save/cancel UX, backend restart-notice surfacing, and unsaved-edit-safe refresh handling.
  - Scope: `frontend/src/api/taskClient.js`, `frontend/src/components/SettingsPanel.jsx`.
  - Key behaviors:
    - Added frontend settings write client method for `POST /settings` and parsed restart semantics headers for UI use.
    - Added editable controls and save/cancel flow for approved fields only: `hardware_profile`, `log_level`, `allow_external_search`, `default_search_provider`, `cache_enabled`.
    - Added loading/saving and success/failure feedback, explicit restart-required/hot-applied notice rendering, and polling-safe protection that preserves local unsaved edits during refresh.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 195 modules transformed.`
      - PASS excerpt: `✓ built in 677ms`

- 2026-03-05 23:00
  - Summary: Completed Milestone 11 / Sub-Task T11.3.1 by adding a minimal settings write API path and then correcting restart semantics so `hardware_profile` is restart-required.
  - Scope: `backend/api/main.py`, `backend/api/schemas.py`, `backend/config/settings.py`, `tests/unit/test_api_settings.py`.
  - Key behaviors:
    - Added additive `POST /settings` write path for the approved minimal editable settings subset, while leaving `GET /settings` unchanged.
    - Enforced restart signaling for `hardware_profile`: `X-Settings-Restart-Required=true`, `X-Settings-Restart-Required-Fields` includes `hardware_profile`, and `hardware_profile` is excluded from hot-applied fields.
    - Preserved existing behavior for other in-scope fields unless required by this correction.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_settings.py -q`
      - PASS excerpt: `6 passed in 0.57s`

- 2026-03-05 22:10
  - Summary: Completed Milestone 11 / Sub-Task T11.2.4 by adding frontend user-facing search/tool failure explanation rendering from projected `/task` failure metadata.
  - Scope: `frontend/src/api/taskClient.js`, `frontend/src/App.jsx`.
  - Key behaviors:
    - Updated `createOrContinueTask(...)` in `frontend/src/api/taskClient.js` to additively return `failure: data.failure`.
    - Updated `frontend/src/App.jsx` to store `failure` on assistant messages and conditionally render inline failure details beneath assistant content when `message.failure` exists.
    - Rendering behavior:
      - `Search failed: <reason>` when `attempted_providers` is present (displayed as `p1 → p2 → ...`).
      - `Tool failed: <reason>` otherwise.
      - Optional `Code: <code>` when present.
    - Success-path behavior unchanged.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 195 modules transformed.`
      - PASS excerpt: `✓ built in 664ms`

- 2026-03-05 22:01
  - Summary: Completed Milestone 11 / Sub-Task T11.2.3 frontend UI handling by updating cache indicator mapping in the header to align with corrected `/health/detailed` cache semantics.
  - Scope: `frontend/src/App.jsx`.
  - Key behaviors:
    - `cache` block missing → `unknown`.
    - `enabled === false` → `disabled`.
    - `enabled === true && connected === true` → `enabled / connected`.
    - `enabled === true && connected === false` → `enabled / disconnected`.
    - Header structure, polling cadence, API calls, and `Diagnostics unavailable` behavior unchanged.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 195 modules transformed.`
      - PASS excerpt: `✓ built in 649ms`

- 2026-03-05 21:50
  - Summary: Completed Milestone 11 / Sub-Task T11.2.3 by unifying cache enablement source-of-truth so runtime cache settings derive from typed `Settings` rather than a separate env parser.
  - Scope: `backend/config/settings.py`, `backend/cache/settings.py`, `tests/unit/test_cache_settings.py`, `tests/unit/test_api_health_detailed.py`, `tests/unit/test_context_builder_cache.py`, `tests/unit/test_tool_executor_cache.py`, `tests/unit/test_redis_client.py`.
  - Key behaviors:
    - Added typed `REDIS_URL` to `backend/config/settings.py`.
    - Rewired `backend/cache/settings.py::load_cache_settings()` to use `Settings()` for `cache_enabled` and `redis_url`.
    - Removed duplicated env parsing for cache enablement.
    - Updated affected unit tests to patch the typed Settings path and added disabled-by-config semantics coverage for `/health/detailed`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_cache_settings.py tests/unit/test_api_health_detailed.py tests/unit/test_context_builder_cache.py tests/unit/test_tool_executor_cache.py tests/unit/test_redis_client.py -q`
      - PASS excerpt: `21 passed in 8.51s`
    - `.\backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 245 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\backend_validation_report_20260305_214725.txt`

- 2026-03-05 21:15
  - Summary: Completed Milestone 11 / Sub-Task T11.2.2 by improving header model indicator readability in frontend rendering while preserving existing behavior.
  - Scope: `frontend/src/App.jsx`.
  - Key behaviors:
    - Updated Model indicator rendering to use CSS ellipsis for long values (no string slicing).
    - Added `title={modelIndicator}` so the full value remains accessible on hover.
    - No changes to polling cadence, data sources, or other UI behavior.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 195 modules transformed.`
      - PASS excerpt: `✓ built in 689ms`

- 2026-03-05 20:52
  - Summary: Completed Milestone 11 / Sub-Task T11.2.1 by upgrading assistant markdown/code rendering with `react-markdown` while preserving existing chat flow and non-assistant rendering behavior.
  - Scope: `frontend/package.json`, `frontend/src/App.jsx`.
  - Key behaviors:
    - Added `react-markdown` dependency in `frontend/package.json`.
    - Updated `frontend/src/App.jsx` to render all assistant messages via `ReactMarkdown`, replacing manual triple-backtick splitting.
    - Added custom `components.code` handling for fenced code blocks (styled `pre/code`, language class preserved) and inline code styling.
    - Non-assistant rendering and send/receive flow unchanged.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `✓ 195 modules transformed.`
      - PASS excerpt: `✓ built in 649ms`

- 2026-03-05 20:42
  - Summary: Completed Milestone 11 / Sub-Task T11.1.3 by projecting structured search/tool failure details through task response while preserving existing success payload behavior.
  - Scope: `backend/tools/search_tools.py`, `backend/api/schemas.py`, `backend/api/main.py`, `tests/unit/test_search_tools.py`.
  - Key behaviors:
    - Propagated `attempted_providers: list[str]` from provider ladder results into `backend/tools/search_tools.py` search tool result payloads (success + failure paths).
    - Added additive task response models in `backend/api/schemas.py`:
      - `TaskFailureMetadata { reason, attempted_providers, code }`
      - `TaskResponse { task_id, final_state, llm_output, failure? }`
    - Updated `POST /task` in `backend/api/main.py` to use `response_model=TaskResponse` and to optionally project `failure` from structured tool result when `tool_ok` is false.
    - Extended `tests/unit/test_search_tools.py` to assert `attempted_providers` exists and includes expected provider id.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_search_tools.py -q`
      - PASS excerpt: `6 passed in 0.42s`
    - `.\backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 246 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\backend_validation_report_20260305_203749.txt`

- 2026-03-05 20:28
  - Summary: Completed Milestone 11 / Sub-Task T11.1.2 by persisting workflow execution order in task state and adding focused persistence unit coverage.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_workflow_persistence.py`.
  - Key behaviors:
    - Persisted `workflow_execution_order` into task state alongside `workflow_graph` in `backend/controller/controller_service.py`.
    - Added focused unit test `tests/unit/test_controller_workflow_persistence.py` asserting persisted task state includes `workflow_graph` and non-empty `workflow_execution_order`.
    - `/workflow/{task_id}` endpoint logic unchanged.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_workflow_telemetry.py -q`
      - PASS excerpt: `4 passed in 9.52s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_controller_workflow_persistence.py -q`
      - PASS excerpt: `1 passed in 0.61s`
    - `.\backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 246 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\backend_validation_report_20260305_202536.txt`

- 2026-03-05 19:04
  - Summary: Completed Milestone 11 / Sub-Task T11.1.1 by wiring monthly budget projection into `GET /budget` with typed settings-sourced limits and deterministic monthly API validation.
  - Scope: `backend/config/settings.py`, `backend/api/main.py`, `tests/unit/test_api_budget.py`.
  - Key behaviors:
    - Added typed budget limit fields in `backend/config/settings.py`: `DAILY_BUDGET_USD`, `MONTHLY_BUDGET_USD`.
    - Updated `GET /budget` in `backend/api/main.py` to source limits from typed `Settings`, preserve daily projection, and populate `BudgetResponse.monthly` using existing rolling-30-day helper `SearchBudgetLedger.get_monthly_summary(...)` mapped to `BudgetPeriod`.
    - Updated `tests/unit/test_api_budget.py` to validate populated monthly payload using deterministic definition-site patching of date key and spent values, without stubbing the monthly helper.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests/unit/test_api_budget.py -q`
      - PASS excerpt: `3 passed in 0.60s`
    - `.\backend\.venv\Scripts\python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 245 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\backend_validation_report_20260305_190244.txt`

- 2026-03-05 05:49
  - Summary: Completed Milestone 10 / Task 10.6 by wiring fixed-seed generation control across settings, API/controller threading, and inference completion calls; fixed-seed drift variance integration test now executes and passes.
  - Scope: `backend/config/settings.py`, `backend/api/main.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/llm_worker_node.py`, `backend/models/local_inference.py`, `tests/unit/test_config.py`, `tests/unit/test_nodes.py`, `tests/unit/test_local_inference.py`, `tests/integration/test_drift_rate_measurement.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python -m pytest tests/unit/test_config.py tests/unit/test_nodes.py tests/unit/test_local_inference.py -v`
      - PASS excerpt: `24 passed, 1 skipped`
    - `./backend/.venv/Scripts/python -m pytest tests/integration/test_drift_rate_measurement.py -v`
      - PASS excerpt: `4 passed`
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS excerpt: `PASS WITH SKIPS: integration: 17 tests, 1 skipped`
      - PASS excerpt: `PASS: tests.integration.test_drift_rate_measurement::test_model_output_variance_fixed_seed`
      - PASS excerpt: `INTEGRATION: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260305_054018.txt`

- 2026-03-04 20:53
  - Summary: Completed Milestone 10 / Task 10.5 by adding controller latency P95 integration validation with warm-up + 100+ measured runs and controller-overhead isolation from existing DAG timing artifacts.
  - Scope: `tests/integration/test_controller_latency_p95.py`.
  - Key behaviors:
    - Added roadmap-required latency measurement protocol with warm-up + measured runs and percentile reporting (p50/p95/p99), with p95 as the gating metric.
    - Implemented component checks for DAG dispatch overhead and memory access latency across working state, episodic, and semantic paths.
    - Implemented `test_fsm_transition_overhead` as explicit `pytest.skip` with reason: no direct per-transition elapsed timing artifact available.
  - Evidence:
    - `./backend/.venv/Scripts/python -m pytest tests/integration/test_controller_latency_p95.py -v`
      - PASS excerpt: `4 passed, 1 skipped in 79.40s`
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS excerpt: `PASS WITH SKIPS: integration: 17 tests, 2 skipped`
      - PASS excerpt: `INTEGRATION: PASS_WITH_SKIPS`
      - PASS excerpt: `INTEGRATION=PASS_WITH_SKIPS`

- 2026-03-04 20:01
  - Summary: Completed Milestone 10 / Task 10.4 by adding segmented drift-rate integration validation with deterministic offline protocol and explicit fixed-seed prerequisite handling.
  - Scope: `tests/integration/test_drift_rate_measurement.py`.
  - Key behaviors:
    - Added segmented drift measurement and reporting for orchestration, retrieval, and generation with aggregate overall drift calculation.
    - Implemented gates: repeated-input output stability exact-match rate >= 0.95, semantic embedding stability mean cosine similarity >= 0.99, and decision consistency across runs >= 0.95.
    - Implemented fixed-seed variance test as explicit `pytest.skip` with reason `seed control not wired; required for fixed-seed variance test`; documented prerequisite seed-wiring requirement.
    - Omitted BLEU because no BLEU dependency is present in repository dependencies; metrics use cosine similarity and Levenshtein/edit distance.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/integration/test_drift_rate_measurement.py -v`
      - PASS excerpt: `3 passed, 1 skipped in 5.09s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS excerpt: `PASS WITH SKIPS: integration: 12 tests, 1 skipped`
      - PASS excerpt: `INTEGRATION: PASS_WITH_SKIPS`
      - PASS excerpt: `INTEGRATION=PASS_WITH_SKIPS`

- 2026-03-04 19:40
  - Summary: Completed Milestone 10 / Task 10.3 by adding deterministic offline task-success-rate validation across representative agentic scenarios with category-level gates.
  - Scope: `tests/agentic/test_task_success_rate.py`.
  - Key behaviors:
    - Added 50 deterministic offline scenarios across 5 categories (qa, code, tool, search, conversation; 10 each) using `ControllerService` with isolated per-scenario storage roots.
    - Implemented gated metrics: overall success rate >= 0.85 with per-category breakdown + failure analysis; intent classification accuracy >= 0.90; tool execution success rate >= 0.95 for valid sandbox-scoped tool scenarios; validation gate TPR >= 0.95 and FPR <= 0.05.
    - Search scenarios use existing Milestone 8 offline fixtures under `tests/fixtures/search/` via deterministic payload loader injection.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/agentic/test_task_success_rate.py -v`
      - PASS excerpt: `4 passed in 18.99s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope agentic`
      - PASS excerpt: `SUCCESS: agentic: 4 tests`
      - PASS excerpt: `AGENTIC: PASS`
      - PASS excerpt: `AGENTIC=PASS`

- 2026-03-04 19:27
  - Summary: Completed Milestone 10 / Task 10.2 by adding memory recall accuracy integration validation with roadmap-required metric gates over a versioned offline benchmark.
  - Scope: `tests/integration/test_memory_recall_accuracy.py`, `tests/fixtures/retrieval_benchmark/v1/README.md`, `tests/fixtures/retrieval_benchmark/v1/corpus.json`, `tests/fixtures/retrieval_benchmark/v1/queries.json`, `tests/fixtures/retrieval_benchmark/v1/qrels.json`.
  - Key behaviors:
    - Implemented 4 metric tests and gates: semantic precision/recall/MRR at k=1,3,5,10 (gates: Precision@5>=0.95, Recall@10>=0.95), episodic relevance/coverage >=0.95, hybrid NDCG@10 >=0.90, and context-builder top-5 relevance >=0.95.
    - Added deterministic offline benchmark fixtures under `tests/fixtures/retrieval_benchmark/v1/` with committed corpus/query/qrels data.
    - Documented metric definitions and determinism rules in test/fixture docs, using isolated `tmp_path` memory roots for integration runs.
  - Evidence:
    - `./backend/.venv/Scripts/python -m pytest tests/integration/test_memory_recall_accuracy.py -v`
      - PASS excerpt: `4 passed in 1.00s`
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS excerpt: `SUCCESS: integration: 8 tests`
      - PASS excerpt: `INTEGRATION: PASS`

- 2026-03-04 14:46
  - Summary: Completed Milestone 10 / Task 10.1 by adding integration reproducibility validation with Track A-first artifact determinism and explicit volatile-field exclusions.
  - Scope: `tests/integration/test_reproducibility_validation.py`.
  - Key behaviors:
    - Added Track A reproducibility validation via canonicalized artifact equality and explicit volatile-field exclusions; Track B metrics remain non-blocking/report-only.
    - Added roadmap-required replay scenarios: single task replay, multi-turn replay, tool execution replay (sandbox-only), and retrieval integration replay.
    - Enforced deterministic ordered semantic DAG event sequence comparison while excluding raw timing fields (`elapsed_ns`, `start_offset_ns`) from equality.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/integration/test_reproducibility_validation.py -v`
      - PASS excerpt: `4 passed in 2.24s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS excerpt: `INTEGRATION: PASS`
      - PASS excerpt: `INTEGRATION=PASS`

- 2026-03-04 14:42
  - Summary: Course-corrected validation scope routing by splitting Docker-orchestrating replay baseline coverage out of integration scope.
  - Scope: `tests/docker/test_replay_baseline.py`, `scripts/validate_backend.py`.
  - Changes:
    - Moved `tests/integration/test_replay_baseline.py` → `tests/docker/test_replay_baseline.py`.
    - Added `--scope docker` in `scripts/validate_backend.py` to run `tests/docker/**` with docker-scope timeout/visibility handling.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest -q`
      - PASS excerpt: `238 passed, 1 skipped in 50.13s`

- 2026-03-04 05:08
  - Summary: Completed Milestone 9 / Task 9.8 by adding enhanced header status indicators with split liveness and detailed diagnostics polling.
  - Scope: `frontend/src/App.jsx`.
  - Key behaviors:
    - Added `/health/detailed` polling every 30s via centralized client `getDetailedHealth()`, with immediate fetch on mount and interval cleanup on unmount.
    - Preserved existing `/health` liveness polling every 5s via `getHealth()` to drive Online/Offline only.
    - Graceful degradation on detailed poll failure: Online/Offline is unchanged, last-known-good detailed snapshot is preserved, and header shows `Diagnostics unavailable`.
    - Added minimal header indicators derived from detailed snapshot: `Model` and `Cache`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `vite v5.4.21 building for production...`
      - PASS excerpt: `✓ 33 modules transformed.`
      - PASS excerpt: `✓ built in 394ms`

- 2026-03-03 21:15
  - Summary: Completed Milestone 9 / Task 9.7 by adding a read-only SettingsPanel wired to centralized frontend API client methods for settings and budget display.
  - Scope: `frontend/src/components/SettingsPanel.jsx`, `frontend/src/App.jsx`.
  - Key behaviors:
    - Added `frontend/src/components/SettingsPanel.jsx` using centralized client calls `getSettings()` and `getBudget()` via `Promise.all([...])`.
    - Refresh behavior polls every 10 seconds only while panel is open, with interval cleanup on close/unmount.
    - UI includes loading/error/empty states with stable read-only key/value rendering; budget shows daily + monthly, and monthly `null` renders `N/A`.
    - Updated `frontend/src/App.jsx` to add a Settings toggle and mount panel with `isOpen` / `onClose`.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `vite v5.4.21 building for production...`
      - PASS excerpt: `✓ 33 modules transformed.`
      - PASS excerpt: `✓ built in 418ms`

- 2026-03-03 21:03
  - Summary: Completed Milestone 9 / Task 9.6 usability fix by making WorkflowVisualizer treat workflow telemetry 404 polling responses as a neutral not-yet-available state instead of repeated red error rendering.
  - Scope: `frontend/src/components/WorkflowVisualizer.jsx`.
  - Key behaviors:
    - `GET /workflow/{task_id}` 404 during polling is now rendered as neutral `Workflow telemetry not available yet.` (no red error spam for expected transient absence).
    - Telemetry/error availability state is reset on `taskId` change.
    - Execution order section now renders explicit fallback text `None yet.` when order is empty.
    - No backend changes and no new libraries.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `vite v5.4.21 building for production...`
      - PASS excerpt: `✓ 32 modules transformed.`
      - PASS excerpt: `✓ built in 411ms`

- 2026-03-03 20:28
  - Summary: Completed Milestone 9 / Task 9.5 by extending the centralized frontend API client with all Milestone 9 endpoint methods.
  - Scope: `frontend/src/api/taskClient.js`.
  - Key behaviors:
    - Added `getSettings` (`GET /settings`), `getBudget` (`GET /budget`), `getDetailedHealth` (`GET /health/detailed`), `getReadyHealth` (`GET /health/ready`), and `getWorkflow(taskId)` (`GET /workflow/{task_id}` with encoded task id).
    - Retained throw-on-non-OK behavior with route-specific error messages for all new methods.
    - Kept return shapes unchanged by returning `response.json()` without remapping.
  - Evidence:
    - `npm --prefix frontend run build`
      - PASS excerpt: `vite v5.4.21 building for production...`
      - PASS excerpt: `✓ 31 modules transformed.`
      - PASS excerpt: `✓ built in 468ms`

- 2026-03-03 19:51
  - Summary: Completed Milestone 9 / Task 9.4 by enforcing deterministic monotonic offset ordering for workflow telemetry events.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_workflow_telemetry.py`.
  - Key behaviors:
    - Updated `GET /workflow/{task_id}` to sort returned `node_events` deterministically by offset-present first, then `start_offset_ns` ascending, then stable append-index tie-break.
    - Preserved existing behavior for missing tasks (`404`), schema-default responses when telemetry is absent, and malformed telemetry row skip policy.
    - Added `test_workflow_telemetry_orders_events_by_offset_with_missing_offsets_last` to prove offset ordering, missing-offset-last behavior, and deterministic tie handling.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_workflow_telemetry.py -q`
      - PASS excerpt: `4 passed in 10.14s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 234 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_194845.txt`

- 2026-03-03 19:07
  - Summary: Completed Milestone 9 / Task 9.3.2 with documentation-only alignment by adding explicit process-local detailed-health cache semantics note.
  - Scope: `backend/api/main.py`.
  - Key behaviors:
    - Added explicit comment near module-level detailed-health cache state describing in-process/module-memory cache behavior.
    - Documented scope as per worker/process and not shared across workers/pods/instances.
    - Documented TTL as 30 seconds and intended lower-frequency detailed polling usage.
    - No behavior changes and no endpoint shape changes.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_health_detailed.py -q`
      - PASS excerpt: `4 passed in 2.31s`

- 2026-03-03 19:01
  - Summary: Completed Milestone 9 / Task 9.3.1 only by adding a 30s in-process cache for `GET /health/detailed` and deterministic cache-window test coverage.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_health_detailed.py`.
  - Key behaviors:
    - Added 30s per-process in-process cache for `GET /health/detailed` in `backend/api/main.py`.
    - Added `_monotonic_now()` time-source helper in `backend/api/main.py` for deterministic cache behavior in tests.
    - Added deterministic unit test validating cache reuse within TTL and recompute after TTL expiration.
    - No change to `/health` or `/health/ready` in this task.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_health_detailed.py -q`
      - PASS excerpt: `4 passed in 2.34s`
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_health_ready.py tests/unit/test_api_health_detailed.py tests/unit/test_api_schemas.py -q`
      - PASS excerpt: `9 passed in 6.83s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 233 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_155714.txt`

- 2026-03-03 12:56
  - Summary: Completed Milestone 9 / Task 9.2 by adding typed public budget query helpers and deterministic rolling 30-day monthly semantics in the budget module.
  - Scope: `backend/search/budget.py`, `tests/unit/test_search_budget.py`.
  - Key behaviors:
    - Added typed public budget query helpers in `backend/search/budget.py`: `get_daily_summary(...)`, `get_rolling_30d_spent(...)`, `get_monthly_summary(...)`.
    - Rolling monthly semantics are explicit and deterministic: UTC, inclusive end date, 30-day window.
    - Added deterministic unit tests in `tests/unit/test_search_budget.py` covering daily summary parity vs existing behavior, rolling boundary correctness, monthly summary output shape/values, and fail-safe behavior for missing/corrupt ledger.
    - No `/budget` API refactor was performed in this task.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_search_budget.py tests/unit/test_api_budget.py -q`
      - PASS excerpt: `9 passed in 0.58s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 232 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_125112.txt`

- 2026-03-03 12:36
  - Summary: Completed Milestone 9 / Task 9.1 by centralizing `/settings` projection through typed settings and a single canonical projection helper.
  - Scope: `backend/config/settings.py`, `backend/api/main.py`, `tests/unit/test_api_settings.py`.
  - Key behaviors:
    - Added missing typed settings fields in `backend/config/settings.py`: `REDACT_PII_QUERIES=True`, `REDACT_PII_RESULTS=False`, `ALLOW_EXTERNAL_SEARCH=False`, `DEFAULT_SEARCH_PROVIDER="duckduckgo"`, `CACHE_ENABLED=False`.
    - Added `get_safe_config_projection(settings)` returning flat keys aligned to existing `SettingsResponse` (no schema shape change).
    - Updated `GET /settings` to use projection-only flow for `SettingsResponse` construction (no direct env access in API settings path).
    - Extended `tests/unit/test_api_settings.py` to assert new fields are populated and env overrides are deterministic; retained invalid-settings `500` path.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_settings.py tests/unit/test_api_schemas.py tests/unit/test_api.py -q`
      - PASS excerpt: `6 passed in 0.59s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 229 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_123030.txt`

- 2026-03-03 12:00
  - Summary: Completed Milestone 9 / Sub-Task 9.0.6 by adding `GET /workflow/{task_id}` returning `WorkflowTelemetryResponse` using existing task state and episodic DAG telemetry.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_workflow_telemetry.py`.
  - Key behaviors:
    - Added `GET /workflow/{task_id}` returning `WorkflowTelemetryResponse` using existing task state + episodic DAG telemetry.
    - Unknown task returns `404` with `detail="Task not found"`, matching existing `/task/{task_id}` behavior.
    - Schema-aligned defaults are returned when telemetry is absent: `workflow_graph={}`, `workflow_execution_order=[]`, `node_events=[]`.
    - Populated telemetry path maps graph/order from task state and node events from episodic `dag_node_event` decision records.
    - Node event ordering is deterministic by decision `id` ascending; malformed JSON `content` rows are skipped fail-safe.
    - Added dedicated unit tests in `tests/unit/test_api_workflow_telemetry.py` covering 404, defaults, and populated telemetry with malformed+valid row behavior using definition-site patching of `MemoryManager.get_task_state` and `EpisodicMemory.search_decisions`.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_entrypoint.py tests/unit/test_api_schemas.py tests/unit/test_api_workflow_telemetry.py -q`
      - PASS excerpt: `9 passed in 20.09s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 229 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_115716.txt`

- 2026-03-03 11:40
  - Summary: Completed Milestone 9 / Sub-Task 9.0.5 by adding readiness-tier endpoint `GET /health/ready`.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_health_ready.py`.
  - Key behaviors:
    - Added readiness-tier endpoint `GET /health/ready`.
    - Ready path returns `HTTP 200` with deterministic body including `ready=true`, `service`, and `detail="ready"`.
    - Not-ready path returns `HTTP 503` with deterministic payload indicating `ready=false` and `detail="readiness_unavailable"` when `Settings()` or `_build_memory_manager(settings)` fails (via `HTTPException`).
    - Added dedicated unit tests in `tests/unit/test_api_health_ready.py` covering ready and not-ready paths with deterministic patching of `_build_memory_manager`.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_health_detailed.py tests/unit/test_api_health_ready.py -q`
      - PASS excerpt: `6 passed in 7.10s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 226 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_113749.txt`

- 2026-03-03 11:31
  - Summary: Completed Milestone 9 / Sub-Task 9.0.4 by adding `GET /health/detailed` returning `DetailedHealthResponse` with schema-aligned `hardware`, `model`, and `cache` payloads.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_health_detailed.py`.
  - Key behaviors:
    - Added `GET /health/detailed` route returning `DetailedHealthResponse` with schema-aligned component payloads (`hardware`, `model`, `cache`).
    - Implemented deterministic status semantics (`ok` / `degraded`) and top-level failure mapping to `HTTP 500` with `detail="health_details_unavailable"`.
    - Model selection role is evidence-based and uses `role="chat"`, aligned with existing controller role usage and catalog roles.
    - Added dedicated unit tests in `tests/unit/test_api_health_detailed.py` covering schema-aligned ok response, degraded cache-disconnected path, and unavailable `500` path using deterministic definition-site patching.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_settings.py tests/unit/test_api_budget.py tests/unit/test_api_health_detailed.py -q`
      - PASS excerpt: `10 passed in 2.39s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 224 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_112938.txt`

- 2026-03-03 11:22
  - Summary: Completed Milestone 9 / Sub-Task 9.0.3 by adding `GET /budget` returning `BudgetResponse` with daily projection from existing budget ledger/config and `monthly=None`.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_budget.py`.
  - Key behaviors:
    - Added `GET /budget` route returning `BudgetResponse` with daily fields projected from `SearchBudgetConfig` + `SearchBudgetLedger`, and `monthly=None`.
    - Added deterministic failure mapping to `HTTP 500` with `detail="budget_unavailable"` when budget setup/projection fails.
    - Added dedicated unit tests in `tests/unit/test_api_budget.py` covering schema-aligned response, env override, and unavailable path using deterministic definition-site patching for fixed date key behavior.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_entrypoint.py tests/unit/test_api_settings.py tests/unit/test_api_budget.py -q`
      - PASS excerpt: `10 passed in 15.10s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 221 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_105128.txt`

- 2026-03-03 10:36
  - Summary: Completed Milestone 9 / Sub-Task 9.0.2 by adding `GET /settings` in the backend API, returning `SettingsResponse` via projection from typed `Settings` fields only.
  - Scope: `backend/api/main.py`, `tests/unit/test_api_settings.py`.
  - Key behaviors:
    - Added `GET /settings` route with `response_model=SettingsResponse` and projected values from `Settings` (`APP_NAME`, `DEBUG`, `HARDWARE_PROFILE`, `LOG_LEVEL`, `MODEL_PATH`, `DATA_PATH`, `BACKEND_PORT`).
    - Added deterministic settings-load failure mapping to `HTTP 500` with `detail="settings_unavailable"`.
    - Added dedicated unit tests in `tests/unit/test_api_settings.py` covering schema-aligned keys, env-override behavior, and invalid settings path returning `500`.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api.py tests/unit/test_api_entrypoint.py tests/unit/test_api_settings.py -q`
      - PASS excerpt: `7 passed in 15.94s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 218 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_084710.txt`

- 2026-03-03 06:10
  - Summary: Added v1 Pydantic response schemas for Milestone 9 endpoints and minimal instantiation/serialization unit tests (no API wiring).
  - Scope: `backend/api/schemas.py`, `tests/unit/test_api_schemas.py`.
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_schemas.py -q`
      - PASS excerpt: `2 passed in 1.48s`
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260303_060637.txt`

- 2026-03-02 04:36
  - Summary: Preserved strict preferred-provider failure reason in `search_web` so Tavily-specific failures (for example `unauthorized`) are returned instead of being overwritten with `preferred provider unavailable`.
  - Scope: `backend/tools/search_tools.py`, `tests/unit/test_search_tools.py`.
  - Evidence:
    - Unit:
      - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_search_tools.py -q`
        - PASS excerpt: `6 passed in 0.17s`
    - Unit harness:
      - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
        - PASS excerpt: `PASS WITH SKIPS: unit: 213 tests, 1 skipped`
        - PASS report: `reports/backend_validation_report_20260302_043133.txt`
    - Smoke:
      - `./backend/.venv/Scripts/python.exe -c "... ToolCallNode preferred_provider='tavily' ..."`
        - Output excerpt: `CODE provider_unavailable`, `REASON unauthorized`, `PROVIDER None`, `PREFERRED tavily`

- 2026-03-02 03:19
  - Summary: Implemented Task 8.6.2 by adding live DuckDuckGo provider execution via `ddgs` behind existing EXTERNAL/policy/privacy flow, while keeping unit validation deterministic and offline.
  - Scope: `backend/search/providers/ddg.py`, `tests/unit/test_search_provider_ladder.py`.
  - Evidence:
    - Unit:
      - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_provider_contracts.py tests\unit\test_search_provider_ladder.py tests\unit\test_search_tools.py -q`
        - PASS excerpt: `15 passed in 0.20s`
      - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
        - PASS excerpt: `PASS WITH SKIPS: unit: 210 tests, 1 skipped`
        - PASS report: `reports\backend_validation_report_20260302_030838.txt`
    - Smoke:
      - `docker compose exec -T backend sh -lc "SEARCH_SEARXNG_URL=http://127.0.0.1:9/search python -c \"from backend.workflow.nodes.tool_call_node import ToolCallNode; ctx={'task_id':'smoke-862-ddg','tool_call':{'tool_name':'search_web','payload':{'query':'smoke','top_k':3},'external_call':True,'allow_external':True,'sandbox_roots':['/app']}}; out=ToolCallNode().execute(ctx); r=out.get('tool_result',{}); print('TOOL_OK', out.get('tool_ok')); print('CODE', r.get('code')); print('PROVIDER', r.get('provider')); print('ITEMS', len(r.get('items',[]))); print('PROVIDER_LADDER', r.get('attempted_providers')); print('REASON', r.get('reason'))\""`
        - Output excerpt: `TOOL_OK True`, `CODE ok`, `PROVIDER duckduckgo`, `ITEMS 3`

- 2026-03-02 02:38
  - Summary: Completed Task 8.6.1 smoke-only correction pass for live SearXNG path without backend code changes. Restored deterministic live smoke by using baseline-first compose flow, then minimal SearXNG settings mount for JSON plus required `server.secret_key` after explicit runtime error evidence.
  - Scope: `docker-compose.yml`, `backend/config/search/searxng/settings.yml`, `.env`, `CHANGE_LOG.md`.
  - Key behaviors:
    - Baseline attempt (no custom settings mount) started container but host JSON endpoint returned `403` for `format=json`.
    - Minimal mount re-enabled (`/etc/searxng/settings.yml`) with `search.formats: [html, json]`.
    - Added `server.secret_key` only after container log explicitly required it: `server.secret_key is not changed. Please use something else instead of ultrasecretkey.`
    - Compose topology check confirmed backend can resolve `searxng`; backend live URL remained `http://searxng:8080/search` while host smoke used `http://localhost:8080/search`.
  - Evidence:
    - Unit validation commands:
      - `.\\backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_search_provider_contracts.py tests\\unit\\test_search_provider_ladder.py tests\\unit\\test_search_tools.py -q`
        - PASS excerpt: `14 passed in 0.17s`
      - `.\\backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
        - PASS excerpt: `PASS WITH SKIPS: unit: 209 tests, 1 skipped`
        - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
        - PASS report: `reports\\backend_validation_report_20260302_023738.txt`
    - Smoke correction commands:
      - `docker compose logs --no-color --tail=80 searxng`
        - Required-key proof excerpt: `server.secret_key is not changed. Please use something else instead of ultrasecretkey.`
      - `curl.exe -sS -o NUL -w "HTTP=%{http_code}\\n" "http://localhost:8080/search?q=smoke&format=json"`
        - Success excerpt: `HTTP=200`
      - `docker compose exec -T backend python -c "import httpx; r=httpx.get('http://searxng:8080/search', params={'q':'smoke','format':'json'}, timeout=10.0); print('HTTP', r.status_code); j=r.json(); print('HAS_RESULTS', isinstance(j.get('results'), list)); print('RESULT_COUNT', len(j.get('results', [])))"`
        - Success excerpt: `HTTP 200`, `HAS_RESULTS True`, `RESULT_COUNT 32`
      - `docker compose exec -T backend python -c "from backend.workflow.nodes.tool_call_node import ToolCallNode; ctx={'task_id':'smoke-861','tool_call':{'tool_name':'search_web','payload':{'query':'smoke','top_k':3},'external_call':True,'allow_external':True,'sandbox_roots':['/app']}}; out=ToolCallNode().execute(ctx); r=out.get('tool_result',{}); print('TOOL_OK', out.get('tool_ok')); print('CODE', r.get('code')); print('PROVIDER', r.get('provider')); print('ITEMS', len(r.get('items',[])))"`
        - Success excerpt: `TOOL_OK True`, `CODE ok`, `PROVIDER searxng`, `ITEMS 3`

- 2026-03-01 23:20
  - Summary: Implemented Task 8.5 tool surface + policy-bound escalation wiring by adding EXTERNAL `search_web`/`fetch_url` tools with deterministic offline fixture execution, policy-gated outcomes, and conditional ToolCallNode registration.
  - Scope: `backend/tools/search_tools.py`, `backend/workflow/nodes/tool_call_node.py`, `backend/tools/__init__.py`, `tests/unit/test_search_tools.py`.
  - Key behaviors:
    - Added EXTERNAL tool contracts: `search_web` (`SearchWebInput`) and `fetch_url` (`FetchUrlInput`) with ToolRegistry registration helper and dispatch-map builder.
    - Wired ToolCallNode to register/wire search tools only when explicitly requested (`tool_name` is `search_web` or `fetch_url`), preserving default tool surface otherwise.
    - Integrated policy/budget governance via `decide_external_search(...)` + ledger/config inputs; all tool responses include deterministic `policy` decision payload.
    - Added deterministic offline loader injection hooks: provider payload loader for `search_web` and HTML loader for `fetch_url`; no live HTTP/DNS required.
    - Enforced deny layers: executor EXTERNAL gate (`allow_external`) plus tool-level fail-safe deny path; denied policy/budget returns deterministic `permission_denied` or `budget_exceeded` without provider/extraction execution.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_search_tools.py -q`
      - PASS excerpt: `5 passed in 0.18s`
    - `backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 208 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\\backend_validation_report_20260301_231857.txt`

- 2026-03-01 23:10
  - Summary: Implemented Task 8.4 URL extraction layer with offline fixture-driven contract tests by adding deterministic HTML-to-text extraction API and stable fallback behavior without live HTTP integration.
  - Scope: `backend/search/extract.py`, `backend/search/fetch_models.py`, `backend/search/__init__.py`, `tests/fixtures/fetch/article_simple.html`, `tests/fixtures/fetch/article_with_nav.html`, `tests/fixtures/fetch/minimal.html`, `tests/fixtures/fetch/malformed.html`, `tests/unit/test_fetch_extraction_contracts.py`.
  - Key behaviors:
    - Added extraction API `extract_text_from_html(html, *, max_chars=8000)` returning deterministic shape: `ok`, `code`, `text`, `title`, `meta`.
    - Implemented extractor priority order: `trafilatura` (if importable) -> `BeautifulSoup` (if importable) -> stdlib `html.parser` fallback (always available in runtime).
    - Implemented deterministic normalization/truncation: newline normalization (`CRLF/CR -> LF`), per-line whitespace compaction, blank-line cleanup, and stable hard truncation to `max_chars`.
    - Enforced fail-safe behavior with no exception leakage; deterministic error codes include `empty_input` and `extraction_error`.
    - Added offline deterministic fixture tests validating content extraction, nav-heavy handling, empty-input behavior, malformed HTML fail-safety, and truncation/normalization invariants.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_fetch_extraction_contracts.py -q`
      - PASS excerpt: `5 passed in 0.13s`
    - `backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 203 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\\backend_validation_report_20260301_230846.txt`

- 2026-03-01 23:02
  - Summary: Implemented Task 8.3 provider ladder + offline provider contract tests using deterministic fixtures, adding parse-only provider abstraction and fixed-order fallback orchestration without tool wiring or live HTTP execution.
  - Scope: `backend/search/providers/base.py`, `backend/search/providers/searxng.py`, `backend/search/providers/ddg.py`, `backend/search/providers/tavily.py`, `backend/search/providers/ladder.py`, `backend/search/providers/__init__.py`, `backend/search/__init__.py`, `tests/fixtures/search/searxng_ok.json`, `tests/fixtures/search/searxng_empty.json`, `tests/fixtures/search/ddg_ok.json`, `tests/fixtures/search/tavily_ok.json`, `tests/fixtures/search/malformed.json`, `tests/unit/test_search_provider_contracts.py`, `tests/unit/test_search_provider_ladder.py`.
  - Key behaviors:
    - Added canonical Pydantic schema for provider parsing: `SearchResultItem` and `SearchResponse` plus deterministic parse result wrappers.
    - Added deterministic parse result codes/reasons (`ok`, `empty_results`, `parse_error`, `validation_error`) with fail-safe behavior (malformed/empty payloads return structured failure; no outward exception leakage in tests).
    - Added deterministic fallback ladder in fixed order `searxng -> duckduckgo -> tavily`, selecting the first provider with non-empty parsed items.
    - Added optional `payload_loader` hook to ladder for offline fixture-driven tests only; no runtime-facing fixture map parameter required.
    - Added deterministic terminal ladder failure contract: `code="provider_unavailable"`, `reason="no provider returned results"`.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_search_provider_contracts.py tests\\unit\\test_search_provider_ladder.py -q`
      - PASS excerpt: `8 passed in 0.19s`
    - `backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 198 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\\backend_validation_report_20260301_230037.txt`

- 2026-03-01 22:48
  - Summary: Implemented Task 8.2 budget tracker + policy routing by adding a fail-safe local JSON budget ledger and deterministic external-search policy decision function without provider/tool integration.
  - Scope: `backend/search/__init__.py`, `backend/search/budget.py`, `backend/search/policy.py`, `tests/unit/test_search_budget.py`, `tests/unit/test_search_policy.py`.
  - Key behaviors:
    - Added budget ledger at `data/search/budget.json` with fail-safe load behavior (missing/corrupt/malformed file => empty ledger, no crash).
    - Added Pydantic budget/policy models with non-negative validation (`daily_limit_usd`, `per_call_estimate_usd`, `estimated_cost_usd`).
    - Added deterministic policy decision outputs with ASCII codes/reasons: `permission_denied`, `budget_exceeded`, `ok`, `validation_error`.
    - Policy function is read-only for 8.2: it does not mutate ledger state; spend mutation remains only in `record_spend(...)`.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_search_budget.py tests\\unit\\test_search_policy.py -q`
      - PASS excerpt: `6 passed in 0.20s`
    - `backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 190 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS report: `reports\\backend_validation_report_20260301_224205.txt`

- 2026-03-01 22:35
  - Summary: Implemented Task 8.1 by adding an `EXTERNAL` tool permission tier and enforcing deny-by-default executor gating unless `allow_external=True`, with focused hermetic unit tests.
  - Scope: `backend/tools/registry.py`, `backend/tools/executor.py`, `tests/unit/test_tool_executor_external_permission.py`.
  - Key behaviors:
    - Added `PermissionTier.EXTERNAL` to tool registry enum.
    - Added explicit executor permission gate: EXTERNAL tools return `permission_denied` unless `ToolExecutionRequest.allow_external` is true.
    - Preserved existing tier behavior: `READ_ONLY` unchanged, `WRITE_SAFE` still requires `allow_write_safe`, `SYSTEM` remains denied.
  - Evidence:
    - `backend\\.venv\\Scripts\\python.exe -m pytest tests\\unit\\test_tool_executor_external_permission.py -q`
      - PASS excerpt: `4 passed in 0.17s`
    - `backend\\.venv\\Scripts\\python.exe scripts\\validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 184 tests, 1 skipped`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`

- 2026-03-01 11:29
  - Summary: Implemented Task 7.5 by wiring retrieval into `ContextBuilderNode` via dependency-injected retriever usage, injecting deterministic retrieved-context system messaging while preserving existing context/message behavior on fail-safe paths.
  - Scope: `backend/workflow/nodes/context_builder_node.py`, `tests/unit/test_context_builder_retrieval.py`.
  - Key behaviors:
    - Added DI-only retriever support in `ContextBuilderNode` (`retriever` + optional `retrieval_config`) with no local retriever construction fallback.
    - Added deterministic retrieval system-message injection format (`Retrieved Context:` block with `[source]`, `score={:.3f}`, and deterministic truncation with `...`).
    - Added deterministic insertion index: inject after first existing `system` message when present, otherwise at index `0`.
    - Preserved fail-safe behavior: when retriever is absent, query is empty, retriever raises, or retrieval returns empty, node keeps prior behavior and does not alter context shape beyond existing keys.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_context_builder_retrieval.py -q`
      - PASS excerpt: `3 passed in 0.13s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 180 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_112552.txt`

- 2026-03-01 11:18
  - Summary: Implemented Task 7.4 hybrid retriever orchestration by adding a dependency-injected retrieval module that combines working-state, semantic, and episodic sources into the unified 7.1 scoring contract with deterministic ranking.
  - Scope: `backend/retrieval/hybrid_retriever.py`, `backend/retrieval/retrieval_types.py`, `tests/unit/test_hybrid_retriever.py`.
  - Key behaviors:
    - Added `HybridRetriever` with constructor injection for `semantic_store`, `episodic_memory`, `working_state_provider`, and `now_provider`.
    - Added explicit retrieval policy fields to `RetrievalConfig` (semantic/episodic/working-state relevance defaults, recency defaults, decay parameters, and working-state window) to avoid hardcoded scoring constants in retriever logic.
    - Implemented deterministic recency decay (`exp`-based positional/timestamp decay with injected `now_provider`) and deterministic tie-break ranking across mixed sources.
    - Enforced fail-closed input behavior: empty/whitespace query raises `ValueError`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_hybrid_retriever.py -q`
      - PASS excerpt: `4 passed in 0.06s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 177 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_111657.txt`

- 2026-03-01 11:10
  - Summary: Implemented Task 7.3 episodic DB search + index support by adding idempotent search-oriented indexes and deterministic keyword search APIs for decisions and tool calls.
  - Scope: `backend/memory/episodic_db.py`, `tests/unit/test_episodic_db_search.py`.
  - Key behaviors:
    - Added idempotent indexes with `CREATE INDEX IF NOT EXISTS` on `decisions(task_id)`, `decisions(action_type)`, `decisions(id DESC)`, `tool_calls(decision_id)`, `tool_calls(tool_name)`, and `tool_calls(id DESC)`.
    - Added `search_decisions(query, *, limit=20, task_id=None)` and `search_tool_calls(query, *, limit=20, task_id=None)` using parameterized `LIKE` filtering on relevant text fields.
    - Enforced deterministic ordering via `ORDER BY id DESC` (and `ORDER BY tc.id DESC` for tool calls) with deterministic return dict keys.
    - Enforced safe query behavior: empty/whitespace query raises `ValueError` in both search methods; task-scoped filtering supported (`tool_calls` via join to `decisions`).
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_episodic_db_search.py -q`
      - PASS excerpt: `5 passed in 0.57s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 173 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_110851.txt`

- 2026-03-01 10:54
  - Summary: Implemented Task 7.2 semantic-store normalized scoring by adding `search_text()` that converts FAISS L2 distance to unified 0..1 similarity scores (`1 / (1 + distance)`) while preserving existing semantic index persistence behavior.
  - Scope: `backend/memory/semantic_store.py`, `tests/unit/test_semantic_store_search_text.py`.
  - Key behaviors:
    - Added pure helper `_l2_distance_to_similarity(distance)` implementing deterministic distance→similarity normalization with `[0,1]` bounds.
    - Added `search_text(query, top_k)` returning `text`, `metadata`, `vector_id`, raw `distance`, and normalized `similarity_score`.
    - Enforced deterministic output ordering via explicit sort key `(-similarity_score, vector_id)`.
    - Empty or uninitialized semantic index path returns `[]` fail-safe.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_semantic_store_search_text.py -q`
      - PASS excerpt: `4 passed in 0.20s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 168 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_101920.txt`

- 2026-03-01 10:05
  - Summary: Implemented Task 7.1 retrieval types + scoring contract by adding canonical retrieval enums/types and deterministic 0..1 score computation utilities with unit coverage.
  - Scope: `backend/retrieval/__init__.py`, `backend/retrieval/retrieval_types.py`, `tests/unit/test_retrieval_types.py`.
  - Key behaviors:
    - `RetrievalResult.final_score` is derived (not initializer input) via `RetrievalResult.from_scores(...)` to prevent score mismatch drift.
    - `RetrievalConfig` enforces strict validation for `min_final_score_threshold` in `[0.0, 1.0]` (raises on misconfiguration; no clamping).
    - `compute_final_score(...)` deterministically clamps individual input scores to `[0,1]`, applies weighted normalized scoring, and clamps final output to `[0,1]`.
    - `rank_results(...)` sorts by `final_score` descending using stable ordering semantics for equal-score ties.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_retrieval_types.py -q`
      - PASS excerpt: `6 passed in 0.04s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 164 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_084001.txt`

- 2026-03-01 20:33
  - Summary: Completed Task 7.0 + 7.0.1 in one closeout by persisting FAISS index state to `data/semantic/index.faiss` with fail-safe load/rebuild behavior from SQLite metadata and by adding deterministic `DEBUG` normalization plus deterministic settings source precedence to prevent host-environment collisions (for example, `DEBUG=release`) from destabilizing unit validation.
  - Scope: `backend/memory/semantic_store.py`, `tests/unit/test_semantic_store_persistence.py`, `backend/config/settings.py`, `.env.example`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_semantic_store_persistence.py -q`
      - PASS excerpt: `4 passed in 2.09s`
    - `powershell -NoProfile -Command "$env:DEBUG='release'; ./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_config.py -q; $exit=$LASTEXITCODE; Remove-Item Env:DEBUG; exit $exit"`
      - PASS excerpt: `2 passed in 0.11s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `PASS WITH SKIPS: unit: 158 tests, 1 skipped`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS report: `reports/backend_validation_report_20260301_082727.txt`

- 2026-02-25 15:19
  - Summary: Implemented M6.6 cache settings centralization by introducing an env-backed settings source-of-truth and wiring cache enable/TTL behavior into Redis client factory, ContextBuilderNode, and tool executor while preserving fail-safe operation.
  - Scope: `backend/cache/settings.py`, `backend/cache/redis_client.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/tools/executor.py`, `.env.example`, `.env`, `tests/unit/test_cache_settings.py`, `tests/unit/test_context_builder_cache.py`, `tests/unit/test_tool_executor_cache.py`.
  - Key behaviors:
    - Added centralized cache settings model (`load_cache_settings`) with robust boolean parsing for `CACHE_ENABLED` (`1,true,yes,on` => true; `0,false,no,off` => false; case-insensitive; fallback to default).
    - Wired `create_default_redis_client()` to use centralized settings for `REDIS_URL`, `CACHE_ENABLED`, and `CACHE_DEFAULT_TTL`.
    - Wired ContextBuilder cache behavior to centralized `CACHE_ENABLED` gating and `CONTEXT_CACHE_TTL_SECONDS`.
    - Wired tool executor cache behavior to centralized `CACHE_ENABLED` gating and `TOOL_CACHE_TTL_SECONDS` (replacing hardcoded TTL).
    - Updated env templates/defaults in `.env.example` and `.env` for cache settings consistency.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit -q -k cache`
      - PASS excerpt: `24 passed, 130 deselected in 2.64s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS excerpt: `PASS WITH SKIPS: unit: 154 tests, 1 skipped`

- 2026-02-25 15:01
  - Summary: Implemented M6.5 READ_ONLY tool executor caching with deterministic keys, fail-safe Redis behavior, and hermetic cache tests while preserving backward-compatible executor defaults.
  - Scope: `backend/tools/executor.py`, `tests/unit/test_tool_executor_cache.py`.
  - Key behaviors:
    - READ_ONLY-only caching gate: caching is active only when `cache_client` is provided, `enable_caching=True`, tool tier is `READ_ONLY`, and `privacy_wrapper is None`.
    - Deterministic cache keying via `make_cache_key("tool", parts={"tool_name": request.tool_name, "payload": request.payload})`.
    - Cache TTL for stored tool results is `1800` seconds (task-local constant for M6.5 scope).
    - Cached-hit return path uses a shallow copy and sets `cache_hit=True` without mutating the cached object.
    - Fail-safe cache behavior: cache errors degrade to miss/no-cache execution and do not block tool handler execution.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_executor_cache.py -q`
      - PASS excerpt: `3 passed in 0.15s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-25 14:52
  - Summary: Implemented M6.4 Cached Context Builder by adding optional Redis-backed message caching in ContextBuilderNode with deterministic keying, env-driven TTL, fail-safe behavior, and cache metrics instrumentation.
  - Scope: `backend/workflow/nodes/context_builder_node.py`, `tests/unit/test_context_builder_cache.py`, `.env.example`.
  - Key behaviors:
    - Deterministic context cache keys via `make_cache_key("context", parts={"task_id": str(task_id), "turn": int(turn)})`.
    - Context TTL is read from environment variable `CONTEXT_CACHE_TTL_SECONDS` with fallback `3600` for missing/invalid/non-positive values.
    - Fail-safe cache operations: Redis disabled/unavailable/errors do not break context building; node continues with existing working-state/message logic.
    - Metrics recording for category `context`: cache hit path records hit; attempted miss path records miss.
    - Cache hit replaces only message retrieval while preserving node output shape (`working_state` and other existing keys still produced).
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_context_builder_cache.py -q`
      - PASS excerpt: `3 passed in 2.38s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-25 14:24
  - Summary: Implemented M6.3 Cache Metrics Collector as an in-memory global metrics module with deterministic category handling and added focused unit coverage.
  - Scope: `backend/cache/metrics.py`, `tests/unit/test_cache_metrics.py`.
  - Key behaviors:
    - Added `CacheMetrics` counters for `hits`, `misses`, `sets`, `deletes`, and `errors`, plus per-category maps for hit/miss tracking.
    - Category normalization in `record_hit`/`record_miss` maps empty or whitespace-only category values to `general` for deterministic keying.
    - Stable summary output includes both raw float rates (`hit_rate`) and formatted percent strings (`hit_rate_pct`) at top-level and per-category, with sorted category ordering.
    - Added in-memory singleton accessor via module-level `_global_metrics` and `get_metrics()`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_cache_metrics.py -q`
      - PASS excerpt: `5 passed in 0.06s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-25 14:15
  - Summary: Implemented M6.2 cache key policy and serialization helpers with deterministic ordering, ASCII-safe JSON output, versioned keys, and bounded key-length SHA-256 fallback.
  - Scope: `backend/cache/key_policy.py`, `tests/unit/test_cache_keys.py`.
  - Key behaviors:
    - Stable JSON helpers: `dumps_json`/`loads_json` use deterministic settings (`sort_keys=True`, `ensure_ascii=True`, `separators=(",", ":")`).
    - Versioned deterministic keys via `make_cache_key(..., version="v1")` with stable part ordering across dict insertion order.
    - Deterministic long-key fallback: when `max_key_length` is exceeded, key shape becomes `{prefix}:{version}:h:{sha256_hex}`.
    - Float rules for key normalization: non-finite floats (`NaN`, `Inf`, `-Inf`) fail fast with `ValueError`; finite floats normalized using stable `repr(x)` form.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_cache_keys.py -q`
      - PASS excerpt: `6 passed in 0.04s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-25 11:42
  - Summary: Implemented M6.1 Redis client wrapper with fail-safe behavior and added hermetic unit tests that do not require a live Redis server.
  - Scope: `backend/cache/redis_client.py`, `tests/unit/test_redis_client.py`.
  - Key behaviors:
    - Optional import guard via `REDIS_AVAILABLE` so cache client initialization remains safe when Redis package is unavailable.
    - Fail-safe cache operations: unreachable/unavailable Redis does not raise; `get` returns `None`, `set`/`delete` return `False`, and `invalidate_pattern` returns `0`.
    - Test-safe dependency injection: constructor supports `redis_factory` to inject a fake Redis implementation for hermetic tests.
    - Stable deterministic health check shape: `{"enabled": bool, "connected": bool, "message": str}` with ASCII-only messages.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_redis_client.py -q`
      - PASS excerpt: `5 passed in 4.08s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 14:31
  - Summary: Completed Milestone 5 tool I/O privacy wrapping (excluding Task 5.4) by wiring deterministic input/output PII scanning into executor flow, preserving tool behavior while attaching safe redacted output representation.
  - Scope: `backend/security/privacy_wrapper.py`, `backend/tools/executor.py`, `tests/unit/test_tool_executor_privacy.py`, `tests/unit/test_controller_service_integration.py`.
  - Key behaviors:
    - No payload mutation to handlers: tool handlers continue receiving original validated payloads.
    - Additive output contract: tool result dict remains intact and now includes `privacy` metadata plus `redacted_result_text`.
    - Summary-only deterministic audits: emits `pii_detected` and `pii_redacted` events without raw PII content.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_executor_privacy.py -q`
      - PASS excerpt: `7 passed in 0.14s`
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `8 passed in 1.86s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 14:14
  - Summary: Implemented M5.3.2 configurable ToolCallNode audit logger path so privacy-wrapper logging can be directed per tool call while preserving default behavior.
  - Scope: `backend/workflow/nodes/tool_call_node.py`, `tests/unit/test_controller_service_integration.py`.
  - Key behaviors:
    - Added optional `tool_call.audit_log_path` override for audit logger construction.
    - Normalized override via `str(...).strip()` and treated empty/whitespace-only values as absent (fallback to default logger factory).
    - Added hermetic tests that monkeypatch default audit logger creation to temp paths to avoid repo `data/logs` writes.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_controller_service_integration.py -q`
      - PASS excerpt: `7 passed in 1.62s`
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_executor_privacy.py -q`
      - PASS excerpt: `4 passed in 0.10s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 14:03
  - Summary: Wired M5.3.1 privacy wrapper gating into tool execution so external-flagged calls are policy-gated and privacy-audited before dispatch, while non-external calls retain existing behavior.
  - Scope: `backend/tools/executor.py`, `backend/workflow/nodes/tool_call_node.py`, `tests/unit/test_tool_executor_privacy.py`.
  - Key behaviors:
    - Explicit privacy wrapper injection only: executor accepts `privacy_wrapper` and does not create defaults internally.
    - Fail-closed configuration guard: external calls without `privacy_wrapper` return deterministic `configuration_error`.
    - External call privacy flow: deny-by-default unless `allow_external=true`; allowed path emits audit events including `external_call_initiated` and `pii_detected` when applicable.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_tool_executor_privacy.py -q`
      - PASS excerpt: `4 passed in 0.15s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 13:30
  - Summary: Implemented M5.3 privacy-aware external-call gating wrapper with deny-by-default policy, deterministic stringify-whole payload redaction, and security audit trail events for `permission_denied`, `pii_detected`, and `external_call_initiated`.
  - Scope: `backend/security/privacy_wrapper.py`, `tests/unit/test_privacy_wrapper.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_privacy_wrapper.py -q`
      - PASS excerpt: `6 passed in 0.09s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 13:15
  - Summary: Implemented M5.2 Security Audit Logger per roadmap Task 5.2 with JSONL event logging/read-filter support, timezone-aware UTC helper timestamps, and append durability via UTF-8 newline-normalized writes plus flush.
  - Scope: `backend/security/audit_logger.py`, `tests/unit/test_audit_logger.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_audit_logger.py -q`
      - PASS excerpt: `5 passed in 0.07s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-24 12:52
  - Summary: Implemented M5.1 PII Redaction Engine using the roadmap-first API shape (`PIIType`, `PIIMatch`, `RedactionResult`, `PIIRedactor`, `create_default_redactor`) with full v4 regex coverage and exact v4 redaction token/mode parity (`partial` vs `strict`).
  - Scope: `backend/security/redactor.py`, `tests/unit/test_redactor.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python.exe -m pytest tests/unit/test_redactor.py -q`
      - PASS excerpt: `8 passed in 0.03s`
    - `./backend/.venv/Scripts/python.exe scripts/validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-23 14:25
  - Summary: Implemented M4.5 ToolCallNode wiring into controller runtime DAG execution, enabling tool execution through existing executor/registry/sandbox plumbing without altering plan compiler behavior.
  - Scope: `backend/workflow/nodes/tool_call_node.py`, `backend/workflow/__init__.py`, `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`.
  - Key behaviors:
    - Runtime-only DAG augmentation: `tool_call` node is inserted between `context_builder` and `llm_worker` only when `tool_call` input is provided; otherwise graph/trace remains unchanged.
    - No `plan_compiler` edits; FSM transitions unchanged.
    - WRITE_SAFE is deny-by-default unless `allow_write_safe=True` is explicitly provided in `tool_call` input.
    - Tool-call trace reuses standard `dag_node_event` node lifecycle logging (`node_start`/`node_end`/`node_error`).
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_controller_service_integration.py -q`
      - PASS excerpt: `5 passed in 2.06s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_nodes.py -q`
      - PASS excerpt: `9 passed in 0.24s`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS excerpt: `[SUCCESS] Report saved to reports\backend_validation_report_20260223_142522.txt`

- 2026-02-23 13:42
  - Summary: Implemented M4.4 backend-only tool-call execution plumbing with fail-closed validation/dispatch flow and explicit permission gating for write-safe/system tiers.
  - Scope: `backend/tools/executor.py`, `backend/tools/file_tools.py`, `backend/tools/__init__.py`, `tests/unit/test_tool_executor.py`.
  - Key behaviors:
    - Stable fail-closed execution codes: `tool_not_found`, `validation_error`, `permission_denied`, `tool_not_implemented`, `execution_error`.
    - Permission policy: `READ_ONLY` allowed; `WRITE_SAFE` requires `allow_write_safe=True`; `SYSTEM` denied.
    - Deterministic dispatch via explicit tool-name map from file tools.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor.py -q`
      - PASS excerpt: `8 passed in 0.15s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_file_tools.py -q`
      - PASS excerpt: `16 passed in 0.12s`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-23 13:26
  - Summary: Implemented M4.3.2 `search_files` as a sandbox-scoped glob path matcher (no content search), with deterministic sorted results and fail-closed bounded scanning.
  - Scope: `backend/tools/sandbox.py`, `backend/tools/file_tools.py`, `backend/tools/__init__.py`, `tests/unit/test_file_tools.py`.
  - Key bounds:
    - `SearchFilesInput.max_results` is bounded (`ge=1`, `le=1000`) with default `100`.
    - Sandbox search enforces deterministic scan cap `max_visited=20_000` and fails closed with `search_limit_exceeded`.
    - Results are path/name glob matches only and sorted deterministically.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_file_tools.py -q`
      - PASS excerpt: `16 passed in 0.17s`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit -q -k file_tools`
      - PASS excerpt: `16 passed, 70 deselected in 0.47s`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-23 12:12
  - Summary: Implemented M4.3 sandbox-backed core file tools with documented names `read_file`, `list_directory`, and `file_info`, registered via ToolRegistry schema definitions and validated with focused unit coverage.
  - Scope: `backend/tools/file_tools.py`, `backend/tools/sandbox.py`, `backend/tools/__init__.py`, `tests/unit/test_file_tools.py`.
  - Deliverables:
    - Added tool input models and registration for `read_file`, `list_directory`, `file_info`.
    - Added minimal sandbox `file_info` operation so read/list/info filesystem access remains inside Sandbox.
    - Added file-tool tests for out-of-root rejection, in-root success, and deterministic schema export coverage.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_file_tools.py -q`
      - PASS excerpt: `5 passed in 0.17s`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-23 11:36
  - Summary: Implemented M4.2 Sandbox Execution foundation with fail-closed, deterministic local path scoping and bounded file operations; no controller/workflow integration added.
  - Scope: `backend/tools/sandbox.py`, `backend/tools/__init__.py`, `tests/unit/test_sandbox.py`.
  - Key behaviors:
    - `SandboxConfig.allowed_roots` uses immutable tuple paths normalized to resolved absolute roots at initialization for deterministic containment checks.
    - Path guard is symlink-aware for existing targets and resolves non-existent targets via strict parent resolution before join.
    - Bounded operations: `read_text` (`max_read_bytes`), `list_dir` (`max_list_entries`), `write_text` (`max_write_bytes`).
    - Write/delete are toggle-gated with stable fail-closed error codes (`write_not_allowed`, `delete_not_allowed`).
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_sandbox.py -q`
      - PASS excerpt: `8 passed in 0.12s`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`

- 2026-02-23 11:09
  - Summary: Made `scripts/validate_backend.py` console output encoding-safe on Windows by replacing non-ASCII status glyphs with ASCII markers while preserving report semantics.
  - Scope: `scripts/validate_backend.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
      - PASS excerpt: `UNIT=PASS_WITH_SKIPS`
      - PASS excerpt: `[PASS] JARVISv5 backend is VALIDATED WITH EXPECTED SKIPS!`

- 2026-02-23 10:58
  - Summary: Implemented M4.1 Tool Registry foundation with schema export and fail-closed input validation, and added focused unit tests for registration behavior, validation pass/fail, and deterministic schema export ordering.
  - Scope: `backend/tools/registry.py`, `backend/tools/__init__.py`, `tests/unit/test_tool_registry.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_registry.py -q`
      - PASS excerpt: `6 passed in 0.15s`

- 2026-02-23 00:14
  - Summary: Implemented Milestone 3.3 deterministic artifact comparison for repeated replay-baseline runs using canonical workflow-graph and DAG-event equality checks.
  - Scope: `tests/integration/test_replay_baseline.py`.
  - Canonicalization rules: workflow graph normalized to sorted `nodes`, sorted `edges` (`from`,`to`), and stable `entry`; DAG events compared using stable semantic fields (`controller_state`, `event_type`, `node_id`, `node_type`, `success`) plus deterministic error signals (`error_present`, `error_code`) while ignoring volatile fields (`task_id`, `elapsed_ns`, `start_offset_ns`).
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\integration\test_replay_baseline.py -q`
      - PASS excerpt: `1 passed in 48.24s`

- 2026-02-23 00:03
  - Summary: Added Milestone 3 controller latency baseline into the replay baseline harness using monotonic node durations, extending existing DAG event payloads and replay comparison output without refactoring flow.
  - Scope: `backend/controller/controller_service.py`, `tests/integration/test_replay_baseline.py`.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\integration\test_replay_baseline.py -q`
      - PASS excerpt: `1 passed in 95.66s (0:01:35)`
  - Metric label: `controller_latency_baseline_total_elapsed_ns`.
  - Tolerance rule: replay run comparison passes latency baseline when `abs(run1_total_elapsed_ns - run2_total_elapsed_ns) <= max(2_000_000, int(max(run1_total_elapsed_ns, run2_total_elapsed_ns) * 0.10))`.

- 2026-02-22 22:55
  - Summary: Corrected `scripts/validate_backend.py` to be a "real" regreassion test harness
  - Scope: `scripts/validate_backend.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python scripts/validate_backend.py`
      - PASS report: `reports\backend_validation_report_20260222_224533.txt`

- 2026-02-22 22:36
  - Summary: Unblocked integration harness by removing invalid replay-baseline import dependency from the integration test, resolving `ModuleNotFoundError: No module named 'scripts.integration'`.
  - Scope: `tests/integration/test_replay_baseline.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope integration`
      - PASS report: `reports/backend_validation_report_20260222_223240.txt`
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
      - PASS report (unchanged behavior): `reports/backend_validation_report_20260222_223310.txt`

- 2026-02-22 21:35
  - Summary: Documented Milestone 2 deliverables now present in repository: DAG executor with deterministic dependency ordering and cycle detection, plan-to-workflow compiler, and FSM + DAG orchestration with per-node DAG trace events.
  - Scope: `backend/workflow/dag_executor.py`, `backend/workflow/plan_compiler.py`, `backend/controller/controller_service.py`, `backend/controller/fsm.py`, `tests/unit/test_dag_executor.py`, `tests/unit/test_plan_compiler.py`, `tests/unit/test_controller_service_integration.py`.
  - Evidence:
    - `./backend/.venv/Scripts/python -m pytest tests/unit/test_dag_executor.py -q`
    - `./backend/.venv/Scripts/python -m pytest tests/unit/test_plan_compiler.py -q`
      ```text
      1 passed in 0.02s
      ```
    - `./backend/.venv/Scripts/python -m pytest tests/unit/test_controller_service_integration.py -q`
      ```text
      3 passed in 0.76s
      ```
    - `./backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
      ```text
      DOCKER_INFERENCE=PASS
      ```

- 2026-02-22 07:56
  - Summary: Completed basic UX fixes for user functionality. Increased backend completion cap to reduce mid-sentence truncation, removed `Instruction:` leakage from assistant output, and improved frontend multiline/code readability.
  - Scope: `backend/workflow/nodes/llm_worker_node.py`; frontend message rendering/readability in `frontend/src/App.jsx`.
  - Evidence:
    - `docker compose up -d --build --force-recreate frontend`
      ```text
      Image jarvisv5-frontend Built
      Container jarvisv5-frontend-1 Started
      ```
    - `backend/.venv/Scripts/python -c "...task-fd2511d2a8.json..."`
      ```text
      role=assistant
      includesFences=True
      first40='```python\nimport random\nimport string\n\nr'
      ```
    - Verification pointer: single `/task` python-snippet prompt no longer truncated; archived output includes multiline fenced code (see `data/archives/task-fd2511d2a8.json`).
  - Note: Remaining cosmetic issue — fenced code blocks may still show literal backticks in UI in some cases. Next place to investigate: frontend message rendering in `frontend/src/App.jsx` (`renderAssistantContent` / assistant bubble render branch).

- 2026-02-22 05:20
  - Summary: Corrective hygiene entry replacing prior verbose session note with a concise consolidation. Investigated model auto-download behavior (`MODEL_FETCH=missing`), verified end-to-end local model run, and diagnosed response accumulation source.
  - Scope: Investigation-only session across runtime/config surfaces and trace review; no production code changes.
  - Evidence:
    - Root cause (download not starting initially): selected catalog URL for the Qwen medium/heavy model was incorrect at first; after correction, backend logs showed `[model-fetch] downloading missing model ...` and completion.
    - Completion/runtime proof: `models/qwen2.5-coder-7b-instruct.Q4_K_M.gguf` existed with size `4683073536` and `.tmp` absent; one medium-path functional run returned normal output without password/username/reset terms.
    - Accumulation diagnosis: archived task `data/archives/task-a53cce61f6.json` already stored the long `"I'm an AI ... As for 2+2, the answer is 4."` assistant message for `"What's 2+2?"`; frontend (`frontend/src/App.jsx`) renders `response.llm_output` directly (no append logic).

- 2026-02-20 22:27
  - Summary: Completed UI-4 evidence closure pass without code changes. Verified header status transitions with backend stop/start polling, verified header task context display (shortened task id + final state) after send, and verified New Chat clears task context.
  - Scope: Runtime surfaces only (`http://localhost:3001` header behavior, Docker services `jarvisv5-frontend-1`, `jarvisv5-backend-1`, `jarvisv5-redis-1`); no repository source files were modified by this pass.
  - Evidence:
    - `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
      ```text
      NAMES                 STATUS       PORTS
      jarvisv5-frontend-1   Up 7 hours   0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp
      jarvisv5-backend-1    Up 2 hours   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
      jarvisv5-redis-1      Up 8 hours   0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp
      ```
    - `curl -s -S http://localhost:8000/health`
      ```text
      {"status":"ok","service":"JARVISv5-backend"}
      ```
    - `curl -I http://localhost:3001`
      ```text
      HTTP/1.1 200 OK
      ```
    - `docker stop jarvisv5-backend-1` then `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health`
      ```text
      jarvisv5-backend-1
      curl: (7) Failed to connect to localhost port 8000 after 2223 ms: Could not connect to server
      ```
    - `docker start jarvisv5-backend-1` then `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health`
      ```text
      jarvisv5-backend-1
      {"status":"ok","service":"JARVISv5-backend"}
      ```
    - UI observations:
      ```text
      HEADER_STATUS_AFTER_STOP=Offline
      HEADER_STATUS_AFTER_START=Online
      {task_id:"task-9b0869f3f6", final_state:"ARCHIVE"}
      header_short_id=0869f3f6
      NewChat=cleared_task_and_state_to_placeholders
      ```
    - `git status --porcelain`
      ```text
       M frontend/package.json
      ```

- 2026-02-18 15:00
  - Summary: Removed prompt-specific normalization logic, retained general single-turn stop/trim controls, and applied general `name is <Token>` normalization for deterministic recall output.
  - Scope: `backend/workflow/nodes/llm_worker_node.py`
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`
      ```text
      ...                                                                      [100%]
      3 passed in 11.32s
      ```
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
      ```text
      EXIT:0
      ```
    - Report artifact:
      - `reports/backend_validation_report_20260218_145647.txt`
    - Runtime continuation proof:
      ```text
      Task B llm_output="Alice"
      HAS_USERNAME=False
      HAS_PASSWORD=False
      ```

- 2026-02-18 14:51
  - Summary: Added and verified continuation-linked `/task` recall behavior and constrained LLM output to a single assistant turn for deterministic name recall. Recorded M12–M14 evidence for same-task continuation, bounded transcript usage, stop-token constrained generation, and exact-name normalization.
  - Scope: `backend/api/main.py`, `backend/controller/controller_service.py`, `backend/memory/working_state.py`, `backend/memory/memory_manager.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/workflow/nodes/llm_worker_node.py`, `tests/unit/test_api_entrypoint.py`
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`
      ```text
      ...                                                                      [100%]
      3 passed in 11.43s
      ```
    - `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
      ```text
      Docker Inference:  PASS
      EXIT:0
      ```
    - Report artifact:
      - `reports/backend_validation_report_20260218_144702.txt`
    - Runtime two-call evidence (same task linkage):
      ```text
      REQUEST_B {"task_id":"task-198206da85","user_input":"What is my name? Reply with only the name."}
      RESPONSE_B {"task_id":"task-198206da85","final_state":"ARCHIVE","llm_output":"Alice"}
      CHECK EXACT_ALICE=True HAS_USERNAME=False HAS_PASSWORD=False
      ```

- 2026-02-18 13:39
  - Summary: Updated backend validation harness presentation and diagnostics while preserving existing validation semantics. Added scope-isolated status reporting, standardized summary/invariants output, and per-test pytest listing for executed suites.
  - Scope: `scripts/validate_backend.py`
  - Evidence:
    - `backend/.venv/Scripts/python scripts/validate_backend.py`
      ```text
      EXIT:0
      ```
    - Report artifact:
      - `reports\backend_validation_report_20260218_133955.txt`
    - Optional related artifacts from docker-inference/format runs:
      - `reports\backend_validation_report_20260218_132908.txt`
      - `reports\backend_validation_report_20260218_132851.txt`

- 2026-02-18 11:46
  - Summary: Updated host-venv validation behavior to tolerate missing `llama_cpp` in unit node testing and to classify pytest return code 5 (`no tests collected`) as WARN in default backend validation reporting.
  - Scope: `tests/unit/test_nodes.py`, `scripts/validate_backend.py`
  - Evidence:
    - `backend/.venv/Scripts/python -m pytest tests/unit/test_nodes.py -q`
      ```text
      ........                                                                 [100%]
      8 passed in 0.17s
      ```
    - `backend/.venv/Scripts/python scripts/validate_backend.py`
      ```text
      [SUMMARY SECTION]
      Unit Tests: PASS
      Integration Tests: WARN
      Agentic Tests: WARN
      ```
    - Report artifact: `reports/backend_validation_report_20260218_114558.txt`

- 2026-02-18 11:02
  - Summary: Verified Docker backend real inference path for `/task` using llama_cpp and a mounted GGUF model. Confirmed health endpoint, llama_cpp import inside container, and non-empty `llm_output` in task response.
  - Scope: `docker-compose.yml`, `backend/Dockerfile`, `backend/controller/controller_service.py`, `backend/workflow/nodes/llm_worker_node.py`
  - Evidence:
    - `docker compose config`
      ```text
      PASS
      ```
    - `docker compose build backend`
      ```text
      Image jarvisv5-backend Built
      ```
    - `docker compose up -d redis backend`
      ```text
      Container jarvisv5-backend-1 Started
      ```
    - `docker compose exec -T backend python -c "import llama_cpp; print('OK')"`
      ```text
      OK
      ```
    - `Invoke-RestMethod http://localhost:8000/health`
      ```text
      {"status":"ok","service":"JARVISv5-backend"}
      ```
    - `Invoke-RestMethod POST http://localhost:8000/task` (prompt: `Reply with exactly: OK`)
      ```text
      {"task_id":"task-dd535a9112","final_state":"ARCHIVE","llm_output":".\nTheir latest, ..."}
      ```
    - `docker compose logs backend --tail=120`
      ```text
      [model-fetch] using existing model: models/TinyLlama-1.1BChat-v1.0.Q4_K_M.gguf
      INFO:     ... "POST /task HTTP/1.1" 200 OK
      ```

- 2026-02-18 10:54
  - Summary: Implemented and verified auto-download of selected model when missing and `MODEL_FETCH=missing`, with idempotent reuse when model file already exists.
  - Scope: `models/models.yaml`, `.env.example`, `backend/models/model_registry.py`, `backend/controller/controller_service.py`, `tests/unit/test_model_registry.py`
  - Evidence:
    - `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_model_registry.py -q`
      ```text
      6 passed in 0.09s
      ```
    - Runtime log evidence:
      ```text
      [model-fetch] downloading missing model: ... -> models\TinyLlama-1.1BChat-v1.0.Q4_K_M.gguf
      [model-fetch] download complete: ...
      [model-fetch] using existing model: ...
      ```
    - Evidence artifacts:
      - `reports/m1_task1_20260218_105417.json`
      - `reports/m1_task2_20260218_105417.json`
      - `reports/m1_uvicorn_20260218_105417.log`
      - `reports/m1_uvicorn_20260218_105417.err`

- 2026-02-17 12:48
  - Summary: Pivoted to Docker-First execution model (Layer 0). Implemented Workflow Nodes (Router, LLM, Validator) and integrated them into the Controller Service. Created API Entry Point (/task) for external access. Fixed Docker volume mounts and runtime commands to support the new structure.
  - Scope: `backend/Dockerfile` (Multi-stage build), `backend/workflow/nodes/` (all nodes), `backend/controller/controller_service.py` (wiring), `backend/api/main.py` (endpoints), `docker-compose.yml` (volumes, command).
  - Evidence: Docker build succeeded. Tests for nodes and controller integration passed in Docker. Curl to /task returned JSON with task_id and state.

- 2026-02-16 07:55
  - Summary: Integrated workflow nodes into ControllerService deterministic execution path and added integration coverage for graceful node-failure handling.
  - Scope: `backend/controller/controller_service.py`, `tests/unit/test_controller_service_integration.py`
  - Evidence:
    - `docker compose run backend python -m pytest tests/unit/test_controller_service_integration.py -v`
      ```text
      collected 1 item
      tests/unit/test_controller_service_integration.py::test_controller_service_run_executes_nodes_and_handles_llm_gracefully PASSED
      ============================== 1 passed in 0.45s ===============================
      ```

- 2026-02-16 07:31
  - Summary: Added persistent backend source bind mount in compose while preserving data/models mounts, then verified node tests run without manual volume override.
  - Scope: `docker-compose.yml`
  - Evidence:
    - `docker compose run backend python -m pytest tests/unit/test_nodes.py -v`
      ```text
      collected 7 items
      tests/unit/test_nodes.py::test_llm_worker_node_imports_llama_cpp_and_handles_missing_model PASSED
      ============================== 7 passed in 0.53s ===============================
      ```

- 2026-02-16 07:11
  - Summary: Implemented workflow node layer (router/context builder/LLM worker/validator + base node) and validated deterministic node behavior in Docker runtime.
  - Scope: `backend/workflow/nodes/base_node.py`, `backend/workflow/nodes/router_node.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/workflow/nodes/llm_worker_node.py`, `backend/workflow/nodes/validator_node.py`, `backend/workflow/__init__.py`, `tests/unit/test_nodes.py`
  - Evidence:
    - `docker compose run backend python -m pytest tests/unit/test_nodes.py -v`
      ```text
      collected 7 items
      tests/unit/test_nodes.py::test_llm_worker_node_imports_llama_cpp_and_handles_missing_model PASSED
      ============================== 7 passed in 0.53s ===============================
      ```

- 2026-02-16 05:17
  - Summary: Pivoted to Docker-First execution model (Layer 0). Successfully compiled llama-cpp-python and llama.cpp inside a multi-stage Python 3.12 Docker container. Verified API health.
  - Scope: `backend/Dockerfile`, `backend/requirements.txt` (removed `llama-cpp-python` from Host).
  - Evidence: Docker build completed. llama-cpp-python import check passed. Health endpoint returned OK.

- 2026-02-15 07:41
  - Summary: Completed Milestone 4: Deterministic Controller. Implemented Finite State Machine (FSM) and Controller Service orchestration. Cleaned up Host dependencies to align with Docker-First execution model.
  - Scope: `backend/controller/fsm.py`, `backend/controller/controller_service.py`
  - Evidence: Unit tests passed: test_controller_fsm.py and test_controller_service.py.

- 2026-02-14 18:13
  - Summary: Completed Milestone 2: Memory System. Implemented Episodic Trace (SQLite), Working State (JSON), Semantic Memory (FAISS), and unified Memory Manager.
  - Scope: `backend/memory/episodic_db.py`, `backend/memory/working_state.py`, `backend/memory/semantic_store.py`, `backend/memory/memory_manager.py`
  - Evidence: 18 unit tests passed in Validation Harness.

- 2026-02-14 13:34
  - Summary: Completed Milestone 1: Docker Environment & Base API. Established containerized backend/frontend stack, configuration management, and health check endpoint.
  - Scope: docker-compose.yml; backend/Dockerfile; frontend/Dockerfile; backend/api/main.py; backend/config/settings.py; frontend/package.json; frontend/src/App.jsx
  - Evidence:
    - `curl http://localhost:8000/health`
      ```text
      {"status":"ok","service":"JARVISv5-backend"}
      ```
    - `docker compose ps`
      ```text
      jarvisv5-backend-1 ... Up ...
      jarvisv5-frontend-1 ... Up ...
      jarvisv5-redis-1 ... Up ...
      ```

- 2026-02-10 09:35
  - Summary: CHANGE_LOG.md established
  - Scope: CHANGE_LOG.md
  - Evidence: `cat .\CHANGE_LOG.md -head 1`
    ```text
    # CHANGE_LOG.md
    ```