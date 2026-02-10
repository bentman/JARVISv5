# Project.md: JARVISv5 - Local-First AI Assistant

> **Status**: Bootstrap Phase - Initial Structure Creation
> **Last Updated**: 2026-02-07

---

## Vision
Daily-use AI assistant that runs locally, persists memory, and executes tools.

**Core Purpose**: Help with daily work (research, writing, planning, code assistance) using local resources.

**Core Constraints**:
1. **Local-First**: Runs on your machine, no cloud required
2. **Evidence-Gated**: Tests must pass before moving to next component
3. **Minimal Scope**: Build only what's specified, defer everything else
4. **Clean Implementation**: No legacy code references, start fresh

---

## Phase 1 Scope (Target: 4 Weeks)

### Components to Build

**Component 1: Backend API** (Week 1)
- FastAPI server with `/chat` endpoint
- Request: `{message: str}`
- Response: `{response: str, conversation_id: str}`
- Initial implementation: echo response (LLM integration in Component 2)
- Docker-ready (Dockerfile + docker-compose.yml)

**Component 2: LLM Integration** (Week 1-2)
- llama.cpp wrapper for local inference
- Load TinyLlama GGUF model
- Replace echo with actual LLM responses
- Simple prompt template (no complex orchestration)

**Component 3: Frontend UI** (Week 2)
- React + Vite single-page app
- Chat input box + message display
- Calls backend `/chat` endpoint
- Simple, functional, no styling complexity

**Component 4: Memory Persistence** (Week 3)
- SQLite database for conversation history
- Schema: `conversations(id, timestamp, user_msg, assistant_msg)`
- Backend saves each exchange
- Frontend fetches and displays history

**Component 5: Tool Execution** (Week 4)
- Single tool: `read_file(path: str) -> str`
- LLM function calling integration
- Tool registry with JSON schema
- Execute tool, return result to LLM

---

## Success Criteria (End of Phase 1)

System is considered successful when:

✅ **Functional**: Can chat with local LLM via browser
✅ **Persistent**: Conversations saved, history visible after page refresh
✅ **Capable**: Can read local files when asked
✅ **Runnable**: Single command starts entire system (`docker compose up`)
✅ **Tested**: All components have passing tests
✅ **Daily-Usable**: Actually helps with work for 2+ weeks without critical bugs

---

## Architecture (Current Phase 1)

### Backend Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM Runtime**: llama.cpp (via llama-cpp-python)
- **Memory**: SQLite
- **Containerization**: Docker + docker-compose

### Frontend Stack
- **Language**: JavaScript/JSX
- **Framework**: React 18
- **Build Tool**: Vite
- **HTTP Client**: fetch API (native)

### Data Flow
```
User Input (Browser)
  ↓
Frontend (React)
  ↓ HTTP POST /chat
Backend (FastAPI)
  ↓
LLM (llama.cpp)
  ↓ (optional)
Tools (read_file)
  ↓
Memory (SQLite) ← saves conversation
  ↓
Response → Frontend → User
```

---

## Repository Structure

```
JARVISv5/
├── Project.md              # This file - source of truth
├── AGENTS.md              # Agent collaboration rules
├── README.md              # Setup and usage instructions
├── .env.example           # Configuration template
├── .gitignore             # Git exclusions
├── docker-compose.yml     # Service orchestration
│
├── backend/
│   ├── Dockerfile         # Backend container image
│   ├── main.py            # FastAPI application
│   ├── models.py          # Pydantic request/response schemas
│   ├── llm.py             # llama.cpp wrapper
│   ├── memory.py          # SQLite operations
│   ├── tools.py           # Tool registry and execution
│   └── requirements.txt   # Python dependencies
│
├── frontend/
│   ├── Dockerfile         # Frontend container image (production)
│   ├── index.html         # HTML entry point
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   ├── api.js         # Backend API client
│   │   └── main.jsx       # React entry point
│   ├── package.json       # Node dependencies
│   └── vite.config.js     # Vite configuration
│
├── data/                  # SQLite database storage (created at runtime)
├── models/                # GGUF model files (download separately)
│   └── .gitkeep
│
└── tests/
    ├── test_backend.py        # Backend unit tests
    ├── test_llm.py            # LLM integration tests
    ├── test_memory.py         # Memory persistence tests
    ├── test_tools.py          # Tool execution tests
    └── test_integration.py    # End-to-end tests
```

**Total Core Files**: 20 files
**Complexity**: Minimal, single-purpose files

---

## What NOT to Build (Phase 1)

**Deferred to Phase 2+** (only if daily use proves necessary):

- ❌ Voice interface (STT/TTS/wake word)
- ❌ Web search integration
- ❌ Code execution sandbox
- ❌ Semantic memory (vector store)
- ❌ Controller FSM/DAG workflow
- ❌ Multiple LLM models
- ❌ Policy-based cloud escalation
- ❌ Hardware-aware model selection
- ❌ Desktop application shell
- ❌ Observability infrastructure
- ❌ Complex tool sandboxing
- ❌ Multi-user support

**Why Defer**: Prove basics work first. Add complexity only when real usage demands it.

---

## Development Workflow

### For Each Component

1. **Specification**: Clear task description with requirements
2. **Test First**: Write `tests/test_[component].py` with expected behavior
3. **Implementation**: Write component code to make tests pass
4. **Validation**: Run tests, must pass before proceeding
5. **Integration**: Ensure component works with existing system
6. **Evidence**: Document test results and working state
7. **Move Forward**: Only proceed to next component after validation

### Testing Approach

**Unit Tests**: Each component tested in isolation
- `pytest tests/test_backend.py` - API endpoints
- `pytest tests/test_llm.py` - LLM wrapper
- `pytest tests/test_memory.py` - Database operations
- `pytest tests/test_tools.py` - Tool execution

**Integration Tests**: Complete workflows
- `pytest tests/test_integration.py` - User query → LLM → tool → response

**Manual Validation**: Real usage
- Start system: `docker compose up`
- Use browser: Visit http://localhost:5173
- Test workflow: Chat, refresh page (check history), ask to read file

---

## Dependencies

### Backend (Python)
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
llama-cpp-python==0.2.38
python-multipart==0.0.6
pytest==7.4.4
httpx==0.26.0
```

### Frontend (Node)
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "vite": "^5.0.8"
}
```

### System Requirements
- Docker & Docker Compose
- 8GB+ RAM (for TinyLlama inference)
- 5GB disk space (model files)

---

## Phase 1 Timeline

**Week 1**: Backend API + LLM Integration
- Days 1-2: FastAPI server with echo endpoint
- Days 3-5: llama.cpp integration, actual LLM responses
- Milestone: Can send message, get LLM response via curl

**Week 2**: Frontend UI
- Days 1-3: React app with chat interface
- Days 4-5: Integration with backend, polish UI flow
- Milestone: Can chat via browser

**Week 3**: Memory Persistence
- Days 1-2: SQLite schema and operations
- Days 3-4: Backend integration, save conversations
- Day 5: Frontend shows history
- Milestone: History persists across page refreshes

**Week 4**: Tool Execution
- Days 1-2: Tool registry and read_file implementation
- Days 3-4: Function calling integration with LLM
- Day 5: End-to-end testing and validation
- Milestone: Can ask LLM to read files, see contents

**End of Week 4**: Phase 1 complete, start daily use trial

---

## Phase 2 Planning (Future)

**Only proceed to Phase 2 if**:
1. ✅ Phase 1 system used daily for 2+ weeks
2. ✅ No critical bugs preventing daily use
3. ✅ Evidence of which features are actually needed

**Phase 2 Feature Selection**: Based on real usage patterns
- If you use voice commands → Add STT/TTS
- If local knowledge insufficient → Add web search
- If need to run code → Add code execution
- If recall is poor → Add semantic memory

**Phase 2 Approach**: One feature at a time
- 1-2 weeks per feature
- Test-first development
- Validate before next feature
- Evidence-gated progress

---

## Migration from v2/v4 (Optional, Later)

**IF Phase 1 succeeds AND you need specific v2/v4 capabilities**:

**Approach**: Feature extraction, not code porting
1. Use v5 working system daily
2. Identify specific missing feature from v2/v4
3. Understand what that feature did (behavior, not code)
4. Reimplement cleanly in v5 from scratch
5. Test, validate, integrate

**Do NOT**:
- Copy v2/v4 code files
- Port entire services
- Reference old architecture
- Import legacy patterns

**Why**: Clean implementation prevents confusion, reduces technical debt

---

## Key Principles

### Local-First
- Primary compute: Your machine
- Primary storage: Your disk
- Primary control: You
- Cloud usage: Explicit opt-in only

### Evidence-Gated
- No component without tests
- No integration without validation
- No "I think it works" - only "tests pass"
- Evidence required for every claim

### Minimal Scope
- Build only what's specified
- No feature creep
- No "nice to have" additions
- Defer unless proven necessary

### Clean Implementation
- No legacy references
- Simple, readable code
- Single-purpose files
- Clear dependencies

---

## Current Status

**Phase**: Bootstrap - Repository Structure Creation
**Date**: 2026-02-07
**Next Step**: Create initial files, define Component 1 task

---

## Notes for Future Updates

This Project.md is the **single source of truth** for JARVISv5. 

Update this document when:
- Completing a component (mark status)
- Discovering new requirements (document decision)
- Changing architecture (explain why)
- Planning next phase (based on evidence)

Keep this document:
- Concise (< 500 lines)
- Evidence-based (cite real usage, not theory)
- Current (update with each milestone)
- Clear (readable by humans and agents)
