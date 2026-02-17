# Milestone 0: Course Correction and Baseline Stabilization

**Date**: 2026-02-17  
**Status**: Required before proceeding to roadmap-20260217.md Milestone 1

---

## Assessment: What Got Off Track

### 1. Docker Configuration Drift

**Problem**: Two conflicting Docker configurations existed.

**Found**:
- `docker-compose.yml` — current, simplified (backend + frontend + redis)
- `backend/Dockerfile` — current multi-stage (Python 3.12, llama.cpp only)

**Issue**: Historical `.v4` artifacts caused ambiguity about which stack was authoritative.

**Resolution (2026-02-17)**: Removed abandoned `.v4` artifacts (`docker-compose.v4.yml`, `backend/Dockerfile.v4`) from the repository to eliminate drift.

**Legacy Pattern (v2/v3/v4)**: All used multi-stage builds with voice binaries (whisper.cpp, piper) compiled in. v4 specifically had separate validation services in compose.

**What Should Have Been Done**: Either complete the v4 port OR remove the `.v4` files. Half-finished ports create confusion.

---

### 2. Hardware Detection Reality Check (Best-Effort NPU)

**Problem**: Hardware profiler exists, but NPU detection is inherently best-effort unless validated on target hardware.

**Current State** (`backend/models/hardware_profiler.py`):
- Has: CPU detection (psutil), GPU detection (GPUtil/torch)
- Has: best-effort NPU signals (Apple MPS, Intel OpenVINO hints)
- Has: best-effort Qualcomm/Snapdragon NPU signals (`HardwareType.QUALCOMM_NPU` + `_detect_qualcomm_npu()`)
- Still Missing: AMD NPU detection (no XDNA checks)

**Legacy Pattern (github bentman/JARVISv2)**:
- v2 had explicit hardware routing with checksum verification and auto-install scripts
- v2 hardware detection was conservative: CPU_ONLY, GPU_CUDA, GPU_GENERAL — no NPU variants

**Legacy Pattern (github bentman/JARVISv3)**:
- v3 added provider abstraction (llama.cpp/Ollama routing)
- v3 hardware detection was more ambitious but not production-hardened

**What Should Be Done (Approved Direction)**: Keep NPU variants but treat them as best-effort until real-hardware validation exists. Standardize outputs to the lowercase canonical profiles:
- `light`, `medium`, `heavy`, `npu-optimized`

---

### 3. Test Suite Drift

**Problem**: Tests were created but not aligned with CHANGE_LOG claims.

**Found**:
- `test_api_entrypoint.py` validates `/task` entrypoint behavior.
- Evidence and documentation must remain consistent with what is actually implemented and validated.

**Risk**: When evidence logs lag behind code, roadmap and inventory become misleading.

**Legacy Pattern (github bentman/JARVISv3)**:
- v3 had `validate_backend.py` as authoritative regression harness
- v3 had clear separation: unit tests → integration tests → agentic tests → validation harness
- v3 tests were tied to SYSTEM_INVENTORY state

**What Should Have Been Done**: Tests should have been created IN THE SAME WORK SESSION as the implementation, with both logged together in CHANGE_LOG.

---

### 4. API Entry Point Already Exists (Unreported Drift)

**Problem**: Milestone 1 in roadmap-20260217.md said "Close the Entry Point" but it's already closed.

**Found**:
- `backend/api/main.py` has `POST /task` and `GET /task/{task_id}` implemented
- `test_api_entrypoint.py` validates both endpoints
- CHANGE_LOG entry 2026-02-17 12:48 reports this was done

**Roadmap-20260217.md Milestone 1** is already complete. Roadmap must track repo reality.

---

## Previous Accomplishments (github bentman/JARVISv1 - github bentman/JARVISv4) — What Worked

### v2: Conservative Hardware + Model Integrity
- Hardware detection: Simple CPU_ONLY / GPU_CUDA / GPU_GENERAL enum
- Model integrity: Checksum verification before loading
- Model registry: YAML catalog with compatibility matrix
- Auto-install: Scripts to download models with verification

**Lesson**: Don't add NPU support until you can actually test it. Stick to what you can verify.

### v3: Validation Harness + Explicit State Tracking
- `validate_backend.py` as single source of truth for "what works"
- SYSTEM_INVENTORY.md tracked state (Implemented / Verified / Placeholder)
- Docker compose had dedicated validation service
- Test structure: unit → integration → agentic → harness

**Lesson**: Regression harness prevents drift. Run it on every milestone.

### v4: Deterministic Controller + Voice Determinism
- FSM with explicit states (INIT/PLAN/EXECUTE/VALIDATE/COMMIT/ARCHIVE/FAILED)
- Voice lifecycle artifacts for replay
- ControllerService orchestrated FSM + nodes
- Multi-stage Docker build with voice binaries compiled

**Lesson**: Controller pattern works. Voice binaries in Docker work. Don't abandon working patterns.

---

## Milestone 0: Stabilization Tasks

### Task 0.1: Resolve Docker Drift

**Action**:
1. Keep current simplified compose as the authoritative stack.
2. Remove abandoned v4 artifacts (completed).

**Validation**:
```bash
docker compose config
docker compose build backend
```

---

### Task 0.2: Hardware Detection Reality Check

**Action**:
1. Keep NPU variants as best-effort signals.
2. Standardize hardware profile outputs to lowercase canonical values across code+tests.
3. Add validation coverage for any enum variants present.

**Validation**:
```bash
# Run hardware profiler tests
docker compose run backend python -m pytest tests/unit/test_hardware_profiler.py -v
# Verify profile casing matches canonical values: light/medium/heavy/npu-optimized
```

---

### Task 0.3: Test-to-Implementation Alignment

**Action**:
1. Audit all test files in `tests/unit/`
2. Cross-reference with CHANGE_LOG.md and SYSTEM_INVENTORY.md
3. Mark tests as "provisional" if implementation not logged OR log the implementation retroactively with evidence

**Validation**:
```bash
# Run all unit tests
docker compose run backend python -m pytest tests/unit/ -v
# Verify all passing tests correspond to SYSTEM_INVENTORY entries
```

---

### Task 0.4: Update Roadmap to Reflect Current State

**Action**:
1. Update `roadmap-20260217.md` to reflect that Milestone 1 is complete
2. Renumber subsequent milestones
3. Add "Milestone 0 (this)" as prerequisite

**Recommendation**: Milestone 1 "Close the Entry Point" should be marked COMPLETE. Start at Milestone 2 "Working LLM Response".

**Validation**:
```bash
# Verify /task endpoint works
docker compose up -d
curl -X POST http://localhost:8000/task -H "Content-Type: application/json" -d '{"user_input":"hello"}'
# Should return: {"task_id": "...", "final_state": "...", "llm_output": ""}
```

---

### Task 0.5: Regression Harness Baseline

**Action**:
1. Run `scripts/validate_backend.py --scope all`
2. Capture output to `reports/baseline_20260217.txt`
3. Add baseline to SYSTEM_INVENTORY.md as validation proof
4. Add Docker compose validation service (from v4 pattern)

**Validation**:
```bash
docker compose run backend python scripts/validate_backend.py --scope all
# Check reports/ directory for output
# All unit tests should pass, integration/agentic may skip if incomplete
```

---

## Integration into roadmap-20260217.md

**Insert Milestone 0 as prerequisite**:

```markdown
## Milestone 0: Baseline Stabilization (Prerequisite)

**Status**: REQUIRED before Milestone 1  
**Objective**: Resolve drift, align tests with implementations, establish regression baseline

**Tasks**: See Milestone 0 detailed report
**Validation**: All unit tests pass, Docker artifacts cleaned, roadmap updated to reflect current state

---

## Milestone 1: ~~Close the Entry Point~~ COMPLETE (as of 2026-02-17)

**Status**: DONE (API endpoints exist, tests pass)  
**Evidence**: CHANGE_LOG.md 2026-02-17 12:48, test_api_entrypoint.py passes

---

## Milestone 2: Working LLM Response (Actual Next Step)

**What**: Load a real GGUF model...
```

---

## Summary

**Drift Detected**:
- Docker config: 2 versions (.yml vs .v4.yml), .v4 not tracked
- Hardware detection: NPU enums exist but detection incomplete/placeholder
- Test suite: Tests written before implementation logged
- Roadmap: Out of sync (Milestone 1 already complete)

**Course Correction**:
- Task 0.1: Clean up Docker artifacts
- Task 0.2: Fix hardware detection (remove NPU or implement properly)
- Task 0.3: Align tests with CHANGE_LOG
- Task 0.4: Update roadmap to current state
- Task 0.5: Run regression harness, capture baseline

**Historical Pattern from v2/v3/v4**:
- v2: Conservative hardware enum, model integrity checks
- v3: Regression harness prevents drift
- v4: Multi-stage Docker with voice, deterministic controller

**Next Action**: Complete Milestone 0 tasks, then proceed to Milestone 2 (LLM Response) since Milestone 1 is already done.