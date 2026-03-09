## JARVISv5 — Gap Analysis: Verified State vs. `Project.md`

The screenshots confirm T13.4 is live: Memory Search panel renders (Image 2) with query input, results area, and Close button. Settings panel renders (Image 1) with Budget section. Header has Memory / Settings / New Chat buttons.

The following gaps are ordered by the sequence they should be addressed, not sprint batching.

---

### G-A: `search_web` Node Missing from Workflow Engine

**What:** `Project.md` §5.1 lists `search_web` as a named node type — *"Aggregates results from search providers."* The search provider ladder, budget, and policy exist. `tool_call` with `tool_name: "search_web"` is auto-injected for research intent, but there is no dedicated `search_web` node. `ToolCallNode` dispatches it generically. The `search_web` name is referenced in context payloads but resolves to nothing — `backend/workflow/__init__.py` does not export it, and `node_registry` in the controller does not include it.

**Priority:** First — research routing injects it already; the gap is a named node that properly encapsulates search execution, result assembly, and provider ladder invocation rather than routing through the generic tool_call dispatch.

---

### M14: Named `search_web` Node + Research Workflow Closure

*Close the gap between research intent routing (working) and a proper search execution node (missing).*

- **T14.1 — `search_web` Node Implementation** — Create `backend/workflow/nodes/search_web_node.py` implementing the provider ladder call, result aggregation, and context injection. Register in `workflow/__init__.py` and `node_registry`.
- **T14.2 — Research Graph Wires `search_web` Not `tool_call`** — Update controller auto-injection for `intent == "research"` to build a research-specific graph using `search_web` directly, rather than injecting via the generic `tool_call` slot.
- **T14.3 — Unit + Integration Test Coverage** — Router-to-search-web path covered end-to-end; provider ladder results visible in context.

---

### G-B: Model Escalation Policy Not Wired

**What:** `Project.md` §3.3 and §6.3 define escalation policy — configurable rules for cloud model fallback when local resources are insufficient. `settings.py` has `ALLOW_EXTERNAL_SEARCH` but no cloud model escalation fields. `model_registry.py` returns `None` when no local model matches; the controller emits a "local model missing" message rather than attempting an escalation path. There is no escalation policy layer between the model registry and the LLM worker.

---

### M15: Model Escalation Policy

*When local model is absent or insufficient, a policy decision (not a silent failure) governs whether a cloud model is attempted.*

- **T15.1 — Escalation Policy Module** — Add `backend/models/escalation_policy.py`: policy rules (resource constraint triggers, explicit user request, capability gap), configurable enable/disable, and budget gate.
- **T15.2 — Controller Integration** — Replace silent `local_model_missing` fallback with policy evaluation; escalation allowed → attempt configured cloud provider; denied → explicit fail-closed error artifact in context.
- **T15.3 — Settings Surface** — Expose `ALLOW_MODEL_ESCALATION` and `ESCALATION_PROVIDER` in `settings.py` and Settings API/panel.

---

### G-C: Model Integrity Verification Absent

**What:** `Project.md` §6.2 — *"Integrity Verification: Model checksums and validation."* `model_registry.py` calls `ensure_model_present()` (path existence check only). No checksum file, no hash verification, no integrity failure path. Deferred in prior milestones.

---

### M16: Model Integrity Checksums

*Model files are verified before use; tampered or corrupted models are rejected.*

- **T16.1 — Checksum Manifest** — Add `models/checksums.yaml` or sidecar `.sha256` files per model entry in `models.yaml`.
- **T16.2 — Verification in Registry** — `ensure_model_present()` verifies hash before returning path; mismatch raises explicit `model_integrity_error`.
- **T16.3 — Controller Fail Path** — Integrity failure produces explicit error artifact; does not fall through to inference silently.

---

### G-D: UI — Settings Panel Shows Budget Only; Hardware / Privacy / Model Fields Absent

**What:** `Project.md` §3.5 and §11.2 require *"hardware profiles, privacy levels, budget monitoring"* in the Settings panel. Image 1 confirms the Settings & Budget panel renders Daily/Monthly budget fields only. `GET /settings` returns `hardware_profile`, `redact_pii_queries`, `redact_pii_results`, `allow_external_search`, `default_search_provider`, `cache_enabled`, and `model_path` — all of which are absent from the rendered panel. The write path (`POST /settings`) exists on the backend; the frontend does not expose it beyond budget.

---

### M17: Settings Panel Completeness

*All configurable settings surfaced by the API are editable from the UI.*

- **T17.1 — Hardware Profile Selector** — Expose `hardware_profile` (Light / Medium / Heavy / NPU) in the panel with `POST /settings` write path.
- **T17.2 — Privacy Controls** — Expose `redact_pii_queries`, `redact_pii_results`, `allow_external_search` as toggles.
- **T17.3 — Model Path + Search Provider** — Expose `model_path` (text input) and `default_search_provider` (selector) as editable fields.
- **T17.4 — Restart-Required Signaling** — Display `X-Settings-Restart-Required` header response visibly in the panel when set.

---

### G-E: Memory Panel UX — Initial State and Empty Query Feedback

**What:** Image 2 shows the Memory Search panel initialises with "No results." displayed before any query is submitted. This is a cosmetic/UX gap — the empty state shows the zero-results message rather than a neutral prompt-to-search state. Minor but visible on first open.

---

### M17 (additive) or standalone:

- **T17.5 — Memory Panel Initial State** — Show neutral placeholder ("Enter a query to search memory") before first search; reserve "No results." for post-search zero-result state.

---

### G-F: Voice Stack Absent

**What:** `Project.md` §7 defines STT (Whisper), TTS (Piper), and wake word (openWakeWord). `backend/voice/__init__.py` exists but is empty. `Project.md` §11.2 names a Voice Panel as an interface element. Deferred explicitly in M13.

---

### M18: Voice Stack Foundation *(deferred, sequence after M17)*

*Minimum viable voice path: STT input and TTS output, no wake word required for initial milestone.*

- **T18.1 — STT Integration** — `backend/voice/stt.py` wrapping Whisper; transcription returns text string.
- **T18.2 — TTS Integration** — `backend/voice/tts.py` wrapping Piper; text-in, audio-out.
- **T18.3 — Voice API Endpoints** — `POST /voice/transcribe` and `POST /voice/speak`.
- **T18.4 — Voice Panel (Frontend)** — Mic button, transcription preview, TTS playback control; follows existing panel pattern.

---

### G-G: Encryption at Rest Absent

**What:** `Project.md` §8.1 — *"Encryption: Conversation storage encrypted at rest."* SQLite episodic trace and semantic metadata are unencrypted on disk. Deprioritized explicitly in prior milestones.

---

### M19: At-Rest Encryption *(deferred, sequence after M18)*

- **T19.1 — Encryption Strategy Decision** — SQLite-level (SQLCipher) vs. file-level (OS-managed) vs. application-layer; select and document in `Project.md`.
- **T19.2 — Implementation** — Apply selected strategy to episodic and semantic stores.
- **T19.3 — Key Management** — Environment-variable-driven key injection; no hardcoded keys.

---

### G-H: Integration and Agentic Test Suites Are Stubs

**What:** `Project.md` §10.1 requires integration and agentic test tiers. The files exist (`tests/integration/`, `tests/agentic/`) but content has not been verified as substantive. These are not run as part of the standard `pytest tests/unit/` evidence chain used in any milestone to date.

---

### M20: Integration + Agentic Test Activation *(sequence last, requires stable feature set)*

- **T20.1 — Integration Suite Verification** — Audit `tests/integration/` content; confirm latency P95, drift rate, memory recall, and reproducibility tests are runnable against a live stack.
- **T20.2 — Agentic Suite Verification** — Audit `tests/agentic/test_task_success_rate.py`; confirm end-to-end task success measurement is executable.
- **T20.3 — Regression Harness Integration** — `scripts/validate_backend.py` should optionally include integration tier; document invocation in `README.md`.

---

### Summary Table

| ID | Gap | Milestone | Sequence |
|----|-----|-----------|----------|
| G-A | `search_web` node absent; research execution routes through generic `tool_call` | M14 | 1st |
| G-B | Model escalation policy not wired; silent `local_model_missing` failure | M15 | 2nd |
| G-C | Model integrity checksums absent | M16 | 3rd |
| G-D | Settings panel shows budget only; hardware/privacy/model fields missing | M17 | 4th |
| G-E | Memory panel shows "No results." before first query (initial state bug) | M17 additive | 4th |
| G-F | Voice stack empty (`backend/voice/__init__.py` only) | M18 | 5th |
| G-G | At-rest encryption absent | M19 | 6th |
| G-H | Integration and agentic test suites unverified / not in evidence chain | M20 | Last |  