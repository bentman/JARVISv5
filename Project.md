# Project.md: JARVISv5 (Mark5) — Local‑First Agent System

> **Vision Only**
> This document describes the **target architecture and invariants** for JARVISv5. 
> The structure below reflects intended organization and capabilities, **not completed implementation**. 
> The presence of paths in the proposed tree indicates design intent only. This baseline is open to refinement as future agentic development progresses.

---

## 1. 🎯 Vision

JARVISv5 is a **daily‑use personal assistant** that is **local‑first by default** and **policy‑guided for escalation** when local resources are insufficient. It supports day‑to‑day work such as **search, research, writing, planning, and code assistance**, while remaining traceable, reproducible, and privacy‑aware.

### Core Invariants

1. **Local‑First Execution:** Tasks run locally unless policy permits escalation.
2. **Deterministic Control:** A state machine / DAG controls execution, not the LLM.
3. **Externalized Memory:** Working, episodic, and semantic artifacts are the source of truth.
4. **Traceability:** Every action produces replayable artifacts.
5. **Policy‑Bound Escalation:** Cloud usage is explicit, budgeted, and auditable.

---

## 2. 🧭 Product Intent (Pragmatic Scope)

- **Daily Assistant:** search, research synthesis, task planning, code help, and knowledge recall.
- **Voice Optional:** STT/TTS and wake word, but not required for core usage.
- **Minimal Friction:** one‑command start, predictable outputs, and clear failure states.

---

## 3. 🏗️ Target Architecture

### 3.1 Control Plane

- **Controller FSM/DAG:** `INIT → PLAN → EXECUTE → VALIDATE → COMMIT → ARCHIVE`.
- **Plan‑to‑Workflow Compiler:** Converts plan steps into executable nodes.
- **Validation Gates:** Fail‑closed policies with explicit error artifacts.

### 3.2 Memory System

- **Working State:** JSON state for active tasks.
- **Episodic Trace:** SQLite event log for deterministic replay.
- **Semantic Memory:** Vector store + SQLite for retrieval, tagging, and recall.

### 3.3 Model & Routing Layer

- **Local LLM Routing:** GGUF/llama.cpp or local provider abstraction.
- **Hardware‑Aware Selection:** CPU/GPU/NPU profiling.
- **Escalation Policy:** Configurable rules for cloud model fallback.

### 3.4 Tools & Extensions

- **Tool Registry:** JSON‑schema validation for tool calls.
- **Sandboxed Execution:** deterministic tooling with constrained IO.
- **Search Providers:** pluggable sources with privacy redaction.

### 3.5 User Experience

- **Web Client:** chat + workflow status + memory/search controls.
- **Voice Panel:** optional mic/wake word controls (non‑blocking).
- **Settings:** hardware profiles, privacy levels, budget governance.

---

## 4. 🧠 Memory Architecture

### 4.1 Working State (Ephemeral)

- **Storage:** JSON files on disk.
- **Schema:** `task_id`, `goal`, `status`, `current_step`, `completed_steps`, `next_steps`.
- **Lifecycle:** Created at task start, archived upon completion.

### 4.2 Episodic Trace (Immutable)

- **Storage:** SQLite (`decisions`, `tool_calls`, `validations` tables).
- **Function:** Append-only log of every action, input, output, and outcome.
- **Key Feature:** Enables deterministic replay of any episode.

### 4.3 Semantic Memory (Curated)

- **Storage:** Vector embeddings (FAISS) + SQLite metadata.
- **Function:** Stores validated patterns, user preferences, and knowledge.
- **Retrieval:** Hybrid search (semantic similarity + symbolic filtering).
- **Privacy:** Local-first with optional redaction for sensitive content.

---

## 5. ⚙️ Workflow Engine

### 5.1 Node Types

| Node Type | Purpose |
|-----------|---------|
| `router` | Determines task intent (chat, code, research). |
| `context_builder` | Retrieves relevant memory artifacts. |
| `llm_worker` | Executes model inference with injected context. |
| `validator` | Verifies output quality and format compliance. |
| `tool_call` | Invokes registered tools with sandboxed execution. |
| `search_web` | Aggregates results from search providers. |

### 5.2 Execution Flow

1. **Task Received:** User input enters system.
2. **Routing:** `router` node classifies intent.
3. **Context Assembly:** `context_builder` retrieves relevant memory.
4. **Execution:** Workflow DAG executes nodes in dependency order.
5. **Validation:** Each node output validated before proceeding.
6. **Commit:** Successful execution updates memory and returns result.
7. **Archive:** Task state and artifacts stored for replay.

---

## 6. 🖥️ Model & Hardware Integration

### 6.1 Hardware Detection

Automatic profiling of:
- CPU architecture and core count
- GPU vendor, memory, and compute capabilities
- Memory capacity and available resources
- Specialized processors (NPU)

### 6.2 Model Router

- **Local Inference:** GGUF models via llama.cpp.
- **Provider Abstraction:** Standardized interface for local/remote models.
- **Hardware Routing:** Matches model requirements to available hardware.
- **Integrity Verification:** Model checksums and validation.

### 6.3 Escalation Policy

- **Local Priority:** All tasks attempt local execution first.
- **Policy Triggers:** Resource constraints, capability gaps, explicit user request.
- **Budget Governance:** Configurable limits with real-time tracking.
- **Privacy Controls:** Automatic redaction before external API calls.

---

## 7. 🎙️ Voice System

### 7.1 Components

- **STT Engine:** Whisper for speech-to-text.
- **TTS Engine:** Piper for text-to-speech with fallback options.
- **Wake Word:** openWakeWord for activation detection.

### 7.2 Workflow Integration

- **Voice Session:** Dedicated workflow path for continuous conversation.
- **Artifact Lifecycle:** Voice interactions stored as episodic traces.
- **Deterministic Runtime:** Reproducible voice processing with explicit state.

---

## 8. 🔒 Privacy & Security

### 8.1 Data Handling

- **Local-First Processing:** All computation occurs locally by default.
- **Data Classification:** Sensitive content identified and handled appropriately.
- **Selective Redaction:** PII removed before external API calls.
- **Encryption:** Conversation storage encrypted at rest.

### 8.2 Security Implementation

- **Model Integrity:** Checksum verification for all models.
- **Sandboxed Execution:** Tool calls isolated from system.
- **Inter-Component Security:** Secure communication between services.
- **User Controls:** Explicit permissions for data retention and sharing.

---

## 9. 🧰 Operational Stack

### 9.1 Docker Services

- **Backend:** FastAPI application with controller and agents.
- **Frontend:** React web client with Vite build.
- **Redis:** Cache for frequent queries and context snippets.
- **Vector Store:** FAISS or Qdrant for semantic memory.
- **Validation:** Dedicated service for regression testing.

### 9.2 Configuration

- **Environment Variables:** All configuration via `.env` file.
- **Hardware Profiles:** Light, Medium, Heavy, NPU-optimized.
- **Privacy Levels:** Configurable data handling policies.
- **Budget Limits:** Per-provider cost thresholds.

---

## 10. ✅ Verification & Quality

### 10.1 Testing Strategy

- **Unit Tests:** Component-level validation.
- **Integration Tests:** Service interaction verification.
- **Agentic Tests:** End-to-end workflow validation.
- **Regression Harness:** `scripts/validate_backend.py` as authoritative suite.

### 10.2 Success Metrics

| Metric | Target | Definition |
|--------|--------|------------|
| **Reproducibility** | 100% | Replaying episode produces identical artifacts. |
| **Memory Recall** | >95% | Accuracy of retrieving relevant past decisions. |
| **Task Success** | >85% | Tasks completed without human intervention. |
| **Drift Rate** | <5% | Behavioral variance over time. |
| **Latency** | <200ms | P95 Controller overhead (excluding inference). |

---

## 11. 🎨 User Interface

### 11.1 Visual Design

**Palette:**
- Background: Deep navy `#050810`
- Header: `#0a0e1a`
- Panels: `#1a2332`
- Accent: Cyan `#00d4ff`
- User messages: Blue `#3b82f6`
- Success: Green `#10b981`
- Error: Red `#ef4444`

**Typography:**
- System UI stack: `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`
- Header: 32px
- Message text: 18px

**Layout:**
- Full-screen fixed layout
- Top status header
- Scrollable message pane
- Docked input bar

**Components:**
- Message bubbles: 20px rounded corners
- AI bubbles: Cyan border glow
- User bubbles: Solid blue
- Error bubbles: Deep red with red border
- Icons: Lucide React (Bot/User/Wifi/Cpu) in circular avatars

### 11.2 Interface Elements

- **Chat Interface:** Message display with streaming responses and markdown support.
- **Workflow Visualizer:** Live node status and execution graph.
- **Voice Panel:** Microphone controls, wake word indicator, activation feedback.
- **Settings Panel:** Hardware profiles, privacy controls, budget monitoring.
- **Status Indicators:** Real-time system health, model routing, resource usage.

---

## 12. 🛠️ Development Approach

### 12.1 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+
- Modern browser (Chrome, Firefox, Edge)

### 12.2 Quick Start

Single-command deployment:
```bash
docker compose up
```

Access web interface at `http://localhost:3000`

### 12.3 Project Organization

- **Modular Services:** Independently deployable components.
- **Clear Boundaries:** Strict separation between controller, agents, and tools.
- **Configuration-Driven:** All behavior controlled via environment variables.
- **Test-First:** Validation suite guards against regression.

---

## 13. 🗂️ Repository Structure

```text
JARVISv5/
├── backend/                              # Python backend service (control plane, memory, tools, model routing)
│   ├── Dockerfile                        # Backend container image definition
│   ├── api/                              # Backend API surface (chat/workflow/memory/voice/settings)
│   ├── config/                           # Environment-driven configuration (hardware/privacy/budget)
│   ├── controller/                       # Deterministic FSM/DAG orchestration and validation gates
│   ├── memory/                           # Working state, episodic trace, semantic memory access
│   ├── models/                           # Local-first model/provider abstraction and routing policy
│   ├── security/                         # Redaction, permissions, and data protection controls
│   ├── tools/                            # Tool registry and sandboxed execution
│   ├── voice/                            # Optional STT/TTS/wake-word workflow path
│   └── workflow/                         # Executable workflow nodes and runtime engine
├── data/                                 # Local runtime artifacts and memory persistence
│   ├── archives/                         # Archived task artifacts for replay/history
│   ├── cache/                            # Cached context/query artifacts
│   ├── episodic/                         # Immutable episodic trace storage
│   ├── logs/                             # Structured runtime logs
│   ├── retrieval/                        # <Need good description>
│   ├── semantic/                         # Semantic memory index/metadata storage
│   └── working_state/                    # Ephemeral task state JSON files
├── frontend/                             # React web client (chat, status, settings, voice panel)
│   ├── Dockerfile                        # Frontend container image definition
│   └── src/                              # UI application source
│       ├── api/                          # Client API bindings to backend services
│       ├── components/                   # UI components (chat/workflow/voice/settings/status)
│       ├── state/                        # Client-side state management
│       ├── styles/                       # Theme, layout, and global styles
│       └── utils/                        # Shared UI utility helpers
├── models/                               # Local model assets and integrity metadata
├── scripts/                              # Operational utilities and validation helpers
│   └── validate_backend.py               # Authoritative backend regression harness
├── tests/                                # Validation suite
│   ├── agentic/                          # End-to-end workflow validation
│   ├── integration/                      # Service interaction validation
│   └── unit/                             # Component-level validation
├── .env.example                          # Configuration template
├── AGENTS.md                             # Agent workflow and repo operating rules
├── CHANGE_LOG.md                         # Append-only record of completed work
├── docker-compose.yml                    # Root service orchestration entrypoint
├── LICENSE                               # Project license
├── Project.md                            # Source-of-truth vision and architecture definition
├── README.md                             # Setup, run, and usage instructions
└── SYSTEM_INVENTORY.md                   # Capability ledger with verification state
```
