
## Repo Census Pack (JARVISv5)  
**Date:** 2026‑03‑15  
**Scope:** Evidence‑only inventory slices (inspection mode only; no file changes)

---

## 1) Backend Architecture + Main Control Flow ✅

### Summary (current implementation)
- **FastAPI backend** (main.py) is the runtime entrypoint, exposing `/task`, `/settings`, `/budget`, `/health*` endpoints.
- **Core execution engine** is `ControllerService` (controller_service.py), which implements a deterministic FSM (PLAN → EXECUTE → VALIDATE → COMMIT → ARCHIVE) and uses a DAG executor to run workflow nodes.
- **Workflow model** is a simple DAG compiled by plan_compiler.py and executed via dag_executor.py.
- **Workflow nodes** live under `backend/workflow/nodes/*` (RouterNode, ContextBuilderNode, LLMWorkerNode, ToolCallNode, ValidatorNode, SearchWebNode).
- **Memory system** is encapsulated in memory_manager.py, which delegates to:
  - Episodic storage (episodic_db.py)
  - Working-state JSON store (working_state.py)
  - Semantic store (semantic_store.py)
- **Model selection + local-model-first behavior** is in model_registry.py, which reads models.yaml, validates local GGUF model paths, and optionally downloads missing models when `MODEL_FETCH=missing`.
- **Escalation** (local model missing → external provider) is in escalation_policy.py, `backend/models/providers/*`, and controller logic in controller_service.py.

### Key files inspected
- main.py
- controller_service.py
- plan_compiler.py
- dag_executor.py
- `backend/workflow/nodes/*`
- model_registry.py
- memory_manager.py

### Observed constraints/dependencies
- Control flow is **explicit, deterministic, state‑machine driven** (no LLM-driven chaining).
- Workflow graph is **static (router→context→llm→validator)** but can be extended with tool/search nodes based on intent/tool_call.
- Model selection depends on models.yaml + local file presence + `MODEL_FETCH` setting.
- Escalation logic is gated by settings (`ALLOW_MODEL_ESCALATION`, `ESCALATION_PROVIDER`, `ALLOW_OLLAMA_ESCALATION`, etc.) and uses `ApiKeyRegistry` to check key presence.

---

## 2) Settings/Config + .env / .env.example ✅

### Summary (current implementation)
- settings.py uses **pydantic-settings** with .env as source (`SettingsConfigDict(env_file=".env")`).
- Safe projection and editable settings handling are explicitly implemented (including write-back to .env) via:
  - `get_safe_config_projection()`
  - `persist_settings_updates()`
  - `settings_update_restart_semantics()`
- .env.example provides the template; .env exists in repo and is being read at runtime (and written by Settings API).

### Key files inspected
- settings.py
- .env.example
- .env

### Observed constraints/dependencies
- .env is treated as a **runtime persistent configuration store** (and is directly modified by API `/settings` via `persist_settings_updates`).
- Editable settings are limited to a curated list (`EDITABLE_SETTINGS_ENV_KEYS`), and restart semantics are computed (e.g., hardware profile triggers restart-required).
- `Settings` has deterministic precedence: init kwargs > .env file > OS env > file secrets.

### Noted tension (repo vs Project.md)
- **Project.md** describes “Privacy: encryption at rest” and “policy-guided escalation”, but existing settings focus on escalation enablement and budget; no evidence of at‑rest encryption implementation (consistent with Project.md’s “Privacy & Security controls” but not explicitly present in code).

---

## 3) Docker/Runtime Topology ✅

### Summary (current implementation)
- docker-compose.yml defines 4 services:
  - **backend**: built from Dockerfile, exposes port 8000, mounts workspace + data + models, depends on `redis` + `searxng`, and runs `uvicorn backend.api.main:app --reload`.
  - **frontend**: built from Dockerfile, exposes port 3000, depends on backend.
  - **redis**: standard `redis:alpine`.
  - **searxng**: `searxng/searxng:latest`, configured via settings.yml.
- Backend Docker build is **multi-stage**:
  - First stage compiles `llama.cpp` and installs `llama-cpp-python`.
  - Final stage installs deps from requirements.txt and copies code.
- Compose config includes `extra_hosts: host.docker.internal:host-gateway` (required for Ollama host access from container).

### Key files inspected
- docker-compose.yml
- Dockerfile
- Dockerfile
- settings.yml

### Observed constraints/dependencies
- Backend expects the host filesystem to provide models and data (mounted in compose).
- Ollama integration assumes `host.docker.internal` access (container→host).
- The backend Docker command runs with `--reload` (development mode).

---

## 4) Frontend Surface (esp Settings/Config UI) ✅

### Summary (current implementation)
- UI is a **React/Vite app** in src.
- **Settings panel** is implemented in SettingsPanel.jsx and provides:
  - Editable fields for: hardware profile, log level, external search toggle, default search provider, cache toggle, model escalation toggles, escalation provider (dropdown), ollama escalation toggle/model, with restart notices.
  - Budget UI (daily/monthly limits) and readouts.
  - Polling refresh every 10s to sync with server state.
  - Uses taskClient.js to call backend endpoints (`/settings`, `/budget`, `/task`, `/task/stream`).

### Key files inspected
- SettingsPanel.jsx
- taskClient.js

### Observed constraints/dependencies
- Settings UI relies on backend `/settings` responding with `escalation_configured_providers` for provider dropdown list.
- The frontend has no local settings persistence; it relies on backend and .env.
- Provided UI includes explicit read-only `ollama_base_url` (expected to be updated in .env and requires restart).

---

## 5) Validation/Test/Harness Surface ✅

### Summary (current implementation)
- **Primary validation harness**: validate_backend.py (runs unit/integration/agentic/dockers tests, plus Docker inference validation).
- Tests are organized under unit, integration, agentic.
- Backend validation reports are saved under reports with timestamped names.
- Many recent CI-style tasks recorded in CHANGE_LOG.md reflect targeted unit tests (e.g., test_controller_service_integration.py, test_api_settings.py, test_escalation_providers.py).

### Key files inspected
- validate_backend.py
- `tests/unit/*` (referenced via changelog; exact files for settings, controller, providers, etc.)
- reports directory (contains validation run logs)

### Observed constraints/dependencies
- Validation harness assumes backend uses .venv and will run `python -m pytest ...` within it (per AGENTS.md rules).
- Docker inference validation builds and runs compose services and queries `/task` endpoint to ensure end‑to‑end behavior.

---

## 6) External Integrated Services / Providers (Repo + Runtime Config) ✅

### Summary (current implementation)
**Escalation providers (LLM APIs)** (controlled via env keys + settings):
- `openai` (`OPENAI_API_KEY`, openai_provider.py)
- `anthropic` (`ANTHROPIC_API_KEY`, anthropic_provider.py)
- `gemini` (`GEMINI_API_KEY`, gemini_provider.py)
- `grok` (`GROK_API_KEY`, grok_provider.py)
- `ollama` (self‑hosted local HTTP server; settings `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, ollama_provider.py)

**Search providers:**
- `searxng` (Docker service + settings.yml + `SEARCH_SEARXNG_URL`)
- `duckduckgo` (implied by `DEFAULT_SEARCH_PROVIDER` setting and search code paths in ddg.py)
- `tavily` (via `TAVILY_API_KEY` and tavily.py)

**Infrastructure services:**
- Redis (`redis` service in compose; used by redis_client.py)
- Local model inference via `llama-cpp-python` (compiled in Docker build stage via `llama.cpp`)
- Local model catalog (models.yaml, model_registry.py, `MODEL_FETCH` support for downloading from URLs)

### Key files inspected
- `backend/models/providers/*`
- api_keys.py
- .env, .env.example (provider keys and service flags)
- `backend/search/providers/*`
- docker-compose.yml (redis, searxng)
- models.yaml (local model catalog)

---

## High‑Signal Findings (max 8)

1. **Deterministic controller flow** is explicitly coded in controller_service.py (FSM + DAG executor + node logging).
2. **Settings persist to .env** via `persist_settings_updates()`, and restart semantics are computed (some changes hot apply, some require restart).
3. **Settings UI includes Ollama escalation controls** and reads `ollama_base_url` as read‑only (backend enforces this).
4. **Docker compose includes host-gateway mapping** to support Ollama on host (`host.docker.internal`).
5. **Validation harness is strong**: validate_backend.py runs unit tests + docker inference + health endpoints, and records reports under reports.
6. **Escalation providers list is fixed** (openai/anthropic/gemini/grok) and is derived from `ApiKeyRegistry`; missing key means provider is treated as unconfigured.
7. **Local model catalog is YAML-driven** and `ModelRegistry.ensure_model_present` can download missing models when `MODEL_FETCH=missing`.
8. **.env in repo contains actual-looking API keys**, which is notable for handoff/security review (it’s used as runtime config).

---

## Recommended Architect Input Set (smallest focus set)

1. controller_service.py — central execution/state machine + escalation fallback logic.
2. settings.py — settings model, safe projection, persistence, restart semantics.
3. SettingsPanel.jsx — current UI surface for settings/budget and escalation controls.
4. docker-compose.yml + Dockerfile — runtime topology and model inference build.
5. models.yaml + model_registry.py — local model catalog + selection/fetch behavior.
6. validate_backend.py — current validation harness and docker inference smoke path.

---