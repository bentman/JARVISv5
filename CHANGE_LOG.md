# CHANGE_LOG.md
> Append-only record of reported work; corrections may be appended to entries.
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