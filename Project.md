# Project.md — JARVISv5 Product Charter (Current State)

## 1) Project Identity

JARVISv5 is a **deterministic, local-first orchestration product** for agentic task execution.

Its active product identity is built around:
- deterministic orchestration
- local-first inference
- optional search/tools
- optional escalation to external model providers
- settings/control-plane UI
- traceable execution

This document describes the product **as implemented now**.

---

## 2) Current Reality

JARVISv5 currently operates as:

- A Python backend that executes tasks through deterministic controller/workflow paths.
- A local-first model runtime using configured local model assets and routing policy.
- Optional tool and search execution, gated by explicit settings.
- Optional escalation to external providers when enabled and policy permits.
- A frontend control-plane with settings management and operational visibility.
- Traceable task execution with persisted events/artifacts for replay and debugging.

In scope today is reliable orchestration behavior and controllable runtime policy, not speculative subsystem breadth.

---

## 3) Core Product Pillars

### 3.1 Deterministic Orchestration
- Task handling follows explicit controller/workflow logic.
- Execution paths are intended to be reproducible under equivalent inputs and settings.

### 3.2 Local-First Inference
- Local inference is the default operating model.
- External model use is a conditional fallback, not the primary mode.

### 3.3 Optional Search and Tools
- Search and tool access are policy-controlled capabilities.
- External-facing operations are permissioned and configuration-dependent.

### 3.4 Optional Escalation
- Escalation is configurable and budget/policy constrained.
- Provider selection is explicit and controlled through settings.

### 3.5 Settings / Control Plane
- Product behavior is managed through configuration surfaces and settings APIs/UI.
- Operators can tune runtime behavior without redefining core architecture.

### 3.6 Traceable Execution
- The system records execution-relevant events/artifacts for inspection and replay.
- Traceability is a core product property for debugging and governance.

---

## 4) Deferred Strategic Capabilities

The following are intentionally **deferred** and not part of active product scope in this charter:

- **Voice experiences** (for example STT/TTS, wake-word UX, voice-first interaction models).
- Broader speculative subsystem expansions that are not required for the current deterministic orchestration product identity.

---

## 5) Operational Principles and Quality Expectations

- **Current-state truthfulness:** product documentation should describe implemented behavior, not aspirational architecture.
- **Determinism-first:** prioritize reproducibility and explicit control over opaque autonomy.
- **Local-first bias:** keep primary execution local, with optional external capabilities as policy-gated extensions.
- **Configurability with guardrails:** settings should expose control without undermining safe, predictable execution.
- **Traceability by default:** execution records must support diagnosis, review, and replay.
- **Scope discipline:** avoid expanding commitments beyond active, observable product behavior.
