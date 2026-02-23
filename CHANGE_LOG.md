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
  - Scope: Runtime surfaces only (`http://localhost:3000` header behavior, Docker services `jarvisv5-frontend-1`, `jarvisv5-backend-1`, `jarvisv5-redis-1`); no repository source files were modified by this pass.
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
    - `curl -I http://localhost:3000`
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