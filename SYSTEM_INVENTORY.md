# SYSTEM_INVENTORY.md
> Authoritative capability ledger. This is not a roadmap or config reference. 
> Inventory entries must reflect only observable artifacts in this repository: files, directories, executable code, configuration, scripts, and explicit UI text. 
> Do not include intent, design plans, or inferred behavior.

## Rules
- One component entry = one capability or feature observed in the repository.
- New capabilities go at the top under `## Inventory` and above `## Observed Initial Inventory`.
- Corrections or clarifications go only below the `## Appendix` section.
- Entries must include: 
  - Capability: **Brief Descriptive Component Name** - Date/Time
  - State: Planned, Implemented, Verified, Deferred
  - Location: `Relative File Path(s)`
  - Validation: Method &/or `Relative Script Path(s)`
  - Notes: Optional (1 line max).
  - Do not include environment values, wiring details, or implementation notes.

## States
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command)
- Deferred: intentionally postponed (reason noted)

## Inventory

- Capability: Deterministic DAG executor (ordering + cycle detection) - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/workflow/dag_executor.py`, `tests/unit/test_dag_executor.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_dag_executor.py -q`
  - Notes: Resolves execution order and rejects cyclic workflow graphs.

- Capability: Plan-to-workflow graph compiler - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/workflow/plan_compiler.py`, `tests/unit/test_plan_compiler.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_plan_compiler.py -q`
  - Notes: Compiles current plan artifact into the runtime workflow graph.

- Capability: FSM and DAG orchestration integration with per-node DAG trace events - 2026-02-22 21:35
  - State: Verified
  - Location: `backend/controller/controller_service.py`, `backend/controller/fsm.py`, `tests/unit/test_controller_service_integration.py`
  - Validation: `./backend/.venv/Scripts/python -m pytest tests/unit/test_controller_service_integration.py -q`; `./backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference`
  - Notes: Controller lifecycle transitions execute DAG phases and emit `dag_node_event` records.

- Capability: UI Header status polling and task-context display/clear behavior (UI-4 evidence pass) - 2026-02-20 22:27
  - State: Verified
  - Location: `frontend/src/App.jsx`, runtime surface `http://localhost:3000`
  - Validation: `docker stop jarvisv5-backend-1`; `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health` (connection failure while stopped); `docker start jarvisv5-backend-1`; `Start-Sleep -Seconds 7; curl -s -S http://localhost:8000/health` (`{"status":"ok","service":"JARVISv5-backend"}`); UI observations `HEADER_STATUS_AFTER_STOP=Offline`, `HEADER_STATUS_AFTER_START=Online`, task context `{task_id:"task-9b0869f3f6", final_state:"ARCHIVE"}`, header short id `0869f3f6`, New Chat clears task/state placeholders
  - Notes: Evidence pass recorded behavior only; no source files modified.

- Capability: LLM output normalization: general single-turn stop + trim (no prompt-specific branching) - 2026-02-18 15:00
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` (`EXIT:0`), report `reports/backend_validation_report_20260218_145647.txt`
  - Notes: Runtime continuation proof returned `Alice` with `HAS_USERNAME=False` and `HAS_PASSWORD=False`.

- Capability: Deterministic “reply with only the name” recall behavior - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`, `tests/unit/test_api_entrypoint.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; runtime `POST /task` continuation sequence with Task B `{"user_input":"What is my name? Reply with only the name."}` returned `llm_output="Alice"`
  - Notes: Verified with same-task continuation and strict equality check.

- Capability: LLM generation constrained to single assistant turn (stop tokens + normalization) - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/workflow/nodes/llm_worker_node.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` (`EXIT:0`); report `reports/backend_validation_report_20260218_144702.txt`; runtime check `HAS_USERNAME=False`, `HAS_PASSWORD=False`
  - Notes: Applies stop markers and first-turn trimming before output is persisted.

- Capability: Working-state transcript persisted across turns (bounded) - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/memory/working_state.py`, `backend/memory/memory_manager.py`, `backend/controller/controller_service.py`, `backend/workflow/nodes/context_builder_node.py`
  - Validation: runtime continuation sequence showed same `task_id` across Task A/Task B and multi-turn transcript retrieval via `GET /task/{task_id}` in prior M12 evidence
  - Notes: Transcript is bounded and reused in prompt history.

- Capability: POST /task continuation via optional task_id - 2026-02-18 14:51
  - State: Verified
  - Location: `backend/api/main.py`, `backend/controller/controller_service.py`, `tests/unit/test_api_entrypoint.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_api_entrypoint.py -q`; runtime Task A/Task B responses showed same `task_id`
  - Notes: Continuation reuses existing task linkage without adding new endpoints.

- Capability: Backend validation harness: per-test pytest listing - 2026-02-18 13:39
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py` (UNIT section lists per-test `✓/✗/○` lines)
  - Notes: Uses pytest `-v` capture with deterministic truncation for long suites.

- Capability: Backend validation harness: standardized report format + invariants - 2026-02-18 13:28
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py` produced summary, invariants, final verdict and report file `reports\backend_validation_report_20260218_133955.txt`
  - Notes: Terminal and report now share consistent structured sections.

- Capability: Backend validation harness: docker-inference scope - 2026-02-18 13:29
  - State: Verified
  - Location: `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python scripts/validate_backend.py --scope docker-inference` with `EXIT:0`; report `reports\backend_validation_report_20260218_132908.txt`
  - Notes: Non-executed unit/integration/agentic suites remain `SKIP` in summary/invariants.

- Capability: Host-Venv Backend Validation Fallback for Missing llama_cpp (M6) - 2026-02-18 11:46
  - State: Verified
  - Location: `tests/unit/test_nodes.py`, `scripts/validate_backend.py`
  - Validation: `backend/.venv/Scripts/python -m pytest tests/unit/test_nodes.py -q`; `backend/.venv/Scripts/python scripts/validate_backend.py`
  - Notes: Node test now records clean import failure path; rc=5 in empty suites is WARN.

- Capability: Model Auto-Fetch on Missing Selected GGUF (M1) - 2026-02-18 10:54
  - State: Verified
  - Location: `backend/models/model_registry.py`, `backend/controller/controller_service.py`, `models/models.yaml`, `.env.example`, `tests/unit/test_model_registry.py`
  - Validation: `backend/.venv/Scripts/python.exe -m pytest tests/unit/test_model_registry.py -q`; runtime logs in `reports/m1_uvicorn_20260218_105417.log` and `reports/m1_uvicorn_20260218_105417.err`
  - Notes: Missing model downloaded once when enabled and reused on subsequent call.

- Capability: Docker Backend Real llama_cpp Inference via /task (M2) - 2026-02-18 11:02
  - State: Verified
  - Location: `docker-compose.yml`, `backend/Dockerfile`, `backend/workflow/nodes/llm_worker_node.py`, `backend/controller/controller_service.py`
  - Validation: `docker compose config`; `docker compose build backend`; `docker compose up -d redis backend`; `docker compose exec -T backend python -c "import llama_cpp; print('OK')"`; `GET /health`; `POST /task` non-empty `llm_output`
  - Notes: Backend container imported llama_cpp and returned non-empty task output.

- Capability: Docker Runtime Environment (Layer 0) - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/Dockerfile`
  - Validation: `docker compose build backend` success.
  - Notes: Multi-stage build compiles llama.cpp and llama-cpp-python from source.

- Capability: Workflow Nodes (Router, LLM, Validator) - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/workflow/nodes/`
  - Validation: `pytest tests/unit/test_nodes.py`
  - Notes: Stateless processing nodes for specific roles.

- Capability: API Entry Point (/task) - 2026-02-17 12:48
  - State: Implemented
  - Location: `backend/api/main.py`
  - Validation: `curl http://localhost:8000/task`
  - Notes: POST endpoint calls ControllerService; GET retrieves state.

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


## Observed Initial Inventory


## Appendix