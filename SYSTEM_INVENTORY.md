# SYSTEM_INVENTORY.md
Authoritative capability ledger. This is not a roadmap or config reference. Inventory entries must reflect only observable artifacts in this repository: files, directories, executable code, configuration, scripts, and explicit UI text. Do not include intent, design plans, or inferred behavior.

## Rules
- One component entry = one capability or feature observed in the repository.
- New capabilities go at the top under `## Inventory` and above `## Observed Initial Inventory:`.
- Entries must include: 
  - Capability: **Brief Descriptive Component Name** - Date/Time
  - State: Planned, Implemented, Verified, Defferred
  - Location: `Relative File Path(s)`
  - Validation: Method &/or `Relative Script Path(s)`
  - Notes: Optional (1 line max).
- Do not include environment values, wiring details, or implementation notes.
- Corrections or clarifications go only below the `## Appendix` section.

## States
- Planned: intent only, not implemented
- Implemented: code exists, not yet validated end-to-end
- Verified: validated with evidence (command)
- Deferred: intentionally postponed (reason noted)

## Inventory

- **Component 5: Tool Execution** - 2026-02-10 12:00
  - State: Planned
  - Location: `backend/tools.py`, `tests/test_tools.py` (planned)
  - Validation: Not yet implemented
  - Notes: Single tool (read_file), LLM function calling integration

- **Component 4: Memory Persistence** - 2026-02-10 12:00
  - State: Planned
  - Location: `backend/memory.py`, `tests/test_memory.py` (planned)
  - Validation: Not yet implemented
  - Notes: SQLite conversation history, schema: conversations(id, timestamp, user_msg, assistant_msg)

- **Component 3: Frontend UI** - 2026-02-10 12:00
  - State: Planned
  - Location: `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/src/main.jsx` (planned)
  - Validation: Not yet implemented
  - Notes: React + Vite chat interface, calls backend /chat endpoint

- **Component 2: LLM Integration** - 2026-02-10 12:00
  - State: Planned
  - Location: `backend/llm.py`, `tests/test_llm.py` (planned)
  - Validation: Not yet implemented
  - Notes: llama.cpp wrapper, TinyLlama GGUF, replaces echo with actual LLM responses

- **Component 1: Backend API** - 2026-02-10 12:00
  - State: Planned
  - Location: `backend/main.py`, `backend/models.py`, `tests/test_backend.py` (planned)
  - Validation: Not yet implemented
  - Notes: FastAPI with /health and /chat endpoints, initial echo implementation


