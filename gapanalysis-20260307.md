## JARVISv5 Gap Analysis — Current State vs. Project.md
*As of 2026-03-07, post-M13*

---

### What is verifiably complete

Controller FSM/DAG, plan compiler, all five workflow node types, memory stack (working/episodic/semantic), hybrid retriever, search providers + ladder, tool registry + sandbox + file tools, PII redactor, privacy wrapper, audit logger, Redis cache layer, hardware profiler, model registry + auto-download, full API surface (`/task`, `/task/stream`, `/task/upload`, `/memory/search`, `/workflow`, `/settings`, `/budget`, `/health/*`), SSE streaming, frontend chat with streaming + markdown + file upload, SettingsPanel, WorkflowVisualizer, MemoryPanel, `state/`, `styles/`, `utils/` modularization, full unit/integration/agentic test suite.

---

### Remaining gaps (code-verified)

---

#### MX1 — Prompt Quality & Inference Depth
*Core daily-use quality gaps — highest daily impact*

| Task | Gap |
|------|-----|
| MX1.1 — Chat-style prompt construction | `LLMWorkerNode` injects `context["messages"]` as flat role-labeled lines (`User: ...`, `Assistant: ...`), not a proper chat template. Models like Qwen/TinyLlama have specific chat templates (`<|im_start|>`, `[INST]`, etc.). No template formatting is applied. |
| MX1.2 — System prompt injection | No system prompt is ever injected at inference time. The four hardcoded instructions (`"You are the assistant..."`) are prepended as raw text, not a `system` message. No per-intent system prompt differentiation (code vs chat vs research). |
| MX1.3 — Research result synthesis | When `intent = research`, the search tool executes and `tool_result` is populated. The `LLMWorkerNode` prompt does not incorporate the search result items — the LLM never sees the retrieved web content. The two paths (search → LLM synthesis) are not connected. |
| MX1.4 — Output token budget | `max_tokens=320` is hardcoded. No per-intent token budget (code responses are typically longer than chat; research synthesis requires more space). |

---

#### MX2 — Escalation Policy & Cloud Model Fallback
*Project.md §6.3, §3.3 — currently absent*

| Task | Gap |
|------|-----|
| MX2.1 — Escalation policy engine | No escalation policy exists. `Project.md` §6.3 defines configurable triggers (resource constraints, capability gaps, explicit request) for cloud model fallback. The model registry selects a local model or returns `None` — there is no fallback to a cloud provider. |
| MX2.2 — Cloud provider abstraction | `LocalInferenceClient` exists. No cloud inference client (OpenAI-compatible, Anthropic, etc.) exists. `Project.md` §6.2 defines a "Provider Abstraction: Standardized interface for local/remote models." |

---

#### MX3 — Security Gaps
*Project.md §8 — partially implemented*

| Task | Gap |
|------|-----|
| MX3.1 — At-rest encryption | `Project.md` §8.1 specifies "Conversation storage encrypted at rest." SQLite episodic trace, working state JSON, and semantic store are all plaintext on disk. |
| MX3.2 — Model integrity checksums | `Project.md` §6.2 specifies "Integrity Verification: Model checksums and validation." `ModelRegistry.ensure_model_present()` downloads and uses GGUF files with no checksum verification. |
| MX3.3 — PII redaction not wired into inference path | `PIIRedactor` exists and privacy wrapper is wired into tool execution. `REDACT_PII_QUERIES=True` is a settings field. But the redactor is never actually called on `user_input` before it enters the prompt or before it is written to episodic memory. The setting has no effect at runtime. |

---

#### MX4 — Validator Completeness
*Project.md §3.1, §5.1 — partially implemented*

| Task | Gap |
|------|-----|
| MX4.1 — Format compliance validation | `ValidatorNode` checks empty, too-short, and model error markers. `Project.md` §5.1 requires "format compliance" validation. No structural or intent-aligned format check exists (e.g., code response actually contains code for a code intent, research response references sources). |
| MX4.2 — Validation written to episodic trace | `EpisodicMemory` has a `validations` table and `log_validation()` method. `ValidatorNode` never calls it. Validation outcomes are in context but not in the trace — they are not replayable. |

---

#### MX5 — Semantic Memory Write Path
*Project.md §4.3 — infrastructure exists, no population path*

| Task | Gap |
|------|-----|
| MX5.1 — Knowledge ingestion from task completions | `SemanticMemory.add_text()` and `MemoryManager.store_knowledge()` exist. Nothing in the controller or workflow ever calls them. Semantic memory is never written during normal task execution — only readable via `/memory/search`. The store is permanently empty unless populated externally. |

---

#### MX6 — Voice System
*Project.md §7 — stub only*

| Task | Gap |
|------|-----|
| MX6.1 — STT/TTS/wake word | `backend/voice/__init__.py` is empty. `Project.md` §7 defines Whisper (STT), Piper (TTS), openWakeWord. No implementation exists. `Project.md` §2 marks this "Voice Optional" — non-blocking for core use. |
| MX6.2 — Voice panel (frontend) | `Project.md` §11.2 and §3.5 name "Voice Panel: microphone controls, wake word indicator." No frontend voice UI exists. |

---

#### MX7 — Operational & Observability Gaps
*Project.md §9, §10*

| Task | Gap |
|------|-----|
| MX7.1 — Structured runtime logs | `Project.md` §13 defines `data/logs/` for structured runtime logs. No log writing to this directory occurs anywhere in the codebase. `LOG_LEVEL` is a settings field but nothing routes structured logs to `data/logs/`. |
| MX7.2 — Qdrant option for vector store | `Project.md` §9.1 lists "FAISS or Qdrant." Only FAISS is implemented. |
| MX7.3 — Privacy level configuration | `Project.md` §9.2 specifies "Privacy Levels: Configurable data handling policies." `REDACT_PII_QUERIES` and `REDACT_PII_RESULTS` exist as settings but are not enforced at runtime (see MX3.3). |

---

### Recommended sequencing

| Order | Milestone | Rationale |
|-------|-----------|-----------|
| 1 | **MX1 — Prompt Quality & Inference Depth** | Most direct daily-use impact. Research synthesis (MX1.3) is a broken loop end-to-end. Chat template formatting (MX1.1) affects every inference call. |
| 2 | **MX3.3 + MX4.2 — PII Wiring + Validation Trace** | Small, high-correctness-value. PII setting currently has no runtime effect. Validation is untraced, breaking replay fidelity. |
| 3 | **MX5.1 — Semantic Memory Write Path** | The memory recall surface (MemoryPanel, `/memory/search`) is live but always returns empty. Closing the write path makes memory actually useful. |
| 4 | **MX4.1 — Validator Format Compliance** | Extends existing validator with intent-aware checks. Depends on MX1 (intent is meaningful) and MX5 (memory has content to validate against). |
| 5 | **MX2 — Escalation Policy & Cloud Fallback** | Completes the local-first + policy-bound escalation invariant. Requires stable local path first (MX1). |
| 6 | **MX3.1 + MX3.2 — At-rest Encryption + Model Checksums** | Security hardening. No daily-use dependency. |
| 7 | **MX7.1 — Structured Logging** | Operational infrastructure. Low user-facing impact. |
| 8 | **MX6 — Voice System** | Explicitly optional per `Project.md` §2. Last. |