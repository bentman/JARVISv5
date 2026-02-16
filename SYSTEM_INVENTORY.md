# SYSTEM_INVENTORY.md
> Authoritative capability ledger. This is not a roadmap or config reference. 
> Inventory entries must reflect only observable artifacts in this repository: files, directories, executable code, configuration, scripts, and explicit UI text. 
>Do not include intent, design plans, or inferred behavior.

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