# Project.md: JARVISv5 (Mark5) — Current Reality & Product Charter

> **Current Reality**
> This document is a living description of what the repository actually implements today. It is not a roadmap or feature wish list.

---

## 1. Current Reality (What Exists Today)

- A **Python FastAPI backend** running a deterministic controller FSM/DAG that orchestrates LLM execution, tool calls, and validation.
- A **React/Vite frontend** (Settings panel + basic UI) talking to the backend via REST endpoints (`/task`, `/settings`, `/budget`, `/health`).
- **Local-first inference** via a model catalog (`models/models.yaml`) and `llama-cpp-python` / GGUF models; missing models can optionally be fetched when `MODEL_FETCH=missing`.
- A **settings/config plane** backed by `.env` and exposed via `/settings`, with a UI for editable settings and a restart-required indicator.
- **Escalation to external providers** (OpenAI/Anthropic/Gemini/Grok, plus Ollama) when local inference is unavailable and policy allows.
- A deterministic **memory system** with working-state JSON, episodic SQLite traces, and semantic recall via FAISS embeddings.
- A **test/validation harness** (`scripts/validate_backend.py`) that runs unit/integration/agentic suites and supports Docker-based inference smoke tests.

---

## 2. Core Identity (Grounded in the Codebase)

### 2.1 Deterministic Orchestration
- All task execution paths are driven by a **controller state machine** and a **workflow graph** (plan → execute → validate → commit → archive).
- The system logs every decision and node event into an append-only episodic trace for replay.

### 2.2 Local‑First Inference
- Local models are selected from a YAML catalog and executed via `llama-cpp-python`.
- Local model execution is the default; escalation is an explicit, opt-in path.

### 2.3 Optional Search/Tools
- Tool calls (including web search via SeaxNG/DuckDuckGo/Tavily) are implemented as pluggable nodes and gated by explicit settings.
- External calls are deny-by-default and require `ALLOW_EXTERNAL_SEARCH=true`.

### 2.4 Optional Escalation
- Escalation is controlled by settings (`ALLOW_MODEL_ESCALATION`, `ESCALATION_PROVIDER`, `ESCALATION_BUDGET_USD`), with provider key presence checked at runtime.
- Ollama escalation is configurable separately (`ALLOW_OLLAMA_ESCALATION`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`).

### 2.5 Settings / Control‑Plane UI
- Settings are editable via the frontend `SettingsPanel`, which writes updated values back to `.env` and reports whether a restart is required.
- The backend exposes a safe projection of settings, and only a subset is editable through the API.

### 2.6 Traceable Execution
- Per-task decisions, node events, and tool call outcomes are persisted and can be replayed for deterministic debugging.

---

## 3. What Is Deferred / Not Present (Clarifying Scope)

- The repository does **not** currently provide **encrypted-at-rest storage** for trace artifacts; this is not implemented.
- There is **no active model checksum verification workflow** or enforced model integrity verification beyond selecting a local model path.
- Voice (STT/TTS) features are not present in the current codebase; any mention in earlier docs is aspirational.

---

## 4. Operational Reality

### 4.1 Runtime Topology
- Docker Compose defines a backend service (FastAPI), frontend (React/Vite), Redis (cache), and SeaxNG (search provider).
- Backend runtime is driven by `.env` and expects local mounts for `models/` and `data/`.

### 4.2 Validation Surface
- `scripts/validate_backend.py` is the canonical validation harness; it runs pytest suites and also supports docker inference smoke tests.
- Unit tests live under `tests/unit`, with integration and agentic suites in `tests/integration` and `tests/agentic`.

---

## 5. Key Repo Paths (Reality Snapshot)

- **Controller / Workflow:** `backend/controller/controller_service.py`, `backend/workflow/`
- **Settings/config:** `backend/config/settings.py`, `.env`, `.env.example`, `backend/api/main.py` (settings endpoints)
- **Model catalog:** `models/models.yaml`, `backend/models/model_registry.py`
- **Escalation providers:** `backend/models/providers/*` and `backend/config/api_keys.py`
- **Frontend settings UI:** `frontend/src/components/SettingsPanel.jsx`, `frontend/src/api/taskClient.js`
- **Validation harness:** `scripts/validate_backend.py`

---

## 6. Tone & Usage

This document is intended for product/architecture readers who want a **grounded view of what is implemented today**, where it is wired, and what can be relied on without guessing. It is **not** a roadmap, nor a list of proposed future capabilities.

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
