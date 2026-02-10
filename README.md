
# J.A.R.V.I.S. AI Local Assistant (Mark5)
## Just A Rewrite, Verging Into Sorcery

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Active](https://img.shields.io/badge/status-Active-green)](#)

JARVISv5 is the latest rewrite in a long line of rewrites.  
It currently does very little, but it does it with suspicious confidence.  
Think of it as a prototype that’s still booting up — the magic tricks come later.

### What This Is
A personal learning project where:
- the architecture is getting cleaner,
- the ideas are getting sharper,
- and the system is *slowly* becoming less of a fire hazard.

### What This Isn’t
- Finished  
- Functional  
- Reliable  
- A benchmark of anything except persistence  

### Why v5 Exists
Because v4 taught me exactly one thing:  
“I can fix this… but only if I start over again.”

### Future Plans
- Make it actually do something  
- Add features that don’t immediately collapse  
- Reduce the number of rewrites per version  
- Eventually become a usable system  

## Quick Start

### Prerequisites

- **Docker** & **Docker Compose**
- **8GB+ RAM** (for local LLM inference)
- **5GB disk space** (for model files)

### Installation

1. **Clone repository**:
   ```bash
   git clone https://github.com/bentman/JARVISv5.git
   pushd JARVISv5
   ```

2. **Download models** (coming soon):
   ```bash
   # Script will be created in Component 2
   ./scripts/download_models.sh
   ```

3. **Start system**:
   ```bash
   docker compose up
   ```

4. **Open browser**:
   ```
   http://localhost:3000
   ```

---

## Project Status

### Phase 1 Components (Target: 4 Weeks)

- [ ] **Component 1**: Backend API (Week 1)
- [ ] **Component 2**: LLM Integration (Week 1-2)
- [ ] **Component 3**: Frontend UI (Week 2)
- [ ] **Component 4**: Memory Persistence (Week 3)
- [ ] **Component 5**: Tool Execution (Week 4)

**Current**: Bootstrap - Repository structure created

---

## What It Does (When Complete)

- 💬 **Chat** with local LLM via browser interface
- 💾 **Remembers** conversation history across sessions
- 📁 **Reads files** when asked (via tool execution)
- 🏠 **Runs locally** - no cloud dependencies
- 🔒 **Privacy-first** - all data stays on your machine

---

## What It Doesn't Do (Yet)

Phase 1 focuses on core functionality. These features are **deferred to Phase 2+**:

- Voice interface (STT/TTS)
- Web search integration
- Code execution
- Semantic memory (vector store)
- Multiple LLM models
- Cloud escalation

**Why**: Prove basics work first, add complexity based on real usage needs.

---

## Architecture

### Stack

**Backend**:
- Python 3.12+
- FastAPI
- llama.cpp (via llama-cpp-python)
- SQLite

**Frontend**:
- React 18
- Vite
- Native fetch API

**Infrastructure**:
- Docker + docker-compose
- Development and production configurations

### Data Flow

```
User Input (Browser)
  ↓
Frontend (React on :3000)
  ↓ HTTP POST /chat
Backend (FastAPI on :8000)
  ↓
LLM (llama.cpp, TinyLlama GGUF)
  ↓ (optional)
Tools (read_file, etc.)
  ↓
Memory (SQLite) ← saves conversation
  ↓
Response → Frontend → User
```

---

## Development

### Local Development (Without Docker)

**Backend**:
```bash
pushd backend
python -m venv .venv
source backend/.venv/bin/activate  # or backend\.venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

---

**Frontend**:
```bash
pushd frontend
npm install
npm run dev
```

---

### Running Tests

```bash
# Backend tests
backend\.venv\Scripts\pytest tests/

# Specific component
backend\.venv\Scripts\pytest tests/test_backend.py -v

# With coverage
backend\.venv\Scripts\pytest --cov=backend tests/
```

## Project Structure

```
JARVISv5/
├── Project.md              # Source of truth - what to build
├── AGENTS.md              # Agent collaboration rules
├── README.md              # This file
├── docker-compose.yml     # Service orchestration
├── .env.example           # Configuration template
│
├── backend/               # Python/FastAPI backend
│   ├── main.py           # API endpoints
│   ├── llm.py            # LLM wrapper
│   ├── memory.py         # Database operations
│   ├── tools.py          # Tool execution
│   └── requirements.txt  # Dependencies
│
├── frontend/             # React frontend
│   ├── src/
│   │   ├── App.jsx       # Main component
│   │   └── api.js        # Backend client
│   └── package.json      # Dependencies
│
├── tests/                # Test suite
│   ├── test_backend.py
│   ├── test_llm.py
│   ├── test_memory.py
│   ├── test_tools.py
│   └── test_integration.py
│
├── data/                 # SQLite database (runtime)
└── models/               # GGUF model files (download)
```

---

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Backend
BACKEND_PORT=8000
MODEL_PATH=/models/tinyllama.gguf
DATABASE_PATH=/data/jarvis.db

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Contributing

### For Agents

Read `AGENTS.md` before starting work. Key rules:

1. **No legacy references** - Don't look at v1/v2/v3/v4 code
2. **Test-first** - Write tests before implementation
3. **Evidence required** - Show test results proving success
4. **Single-file tasks** - One component at a time
5. **Follow specifications** - Build only what's in Project.md

### For Humans

1. Check `Project.md` for current scope and status
2. Propose changes via issues (don't modify specs directly)
3. Follow test-first development
4. Keep changes minimal and focused

---



---

## 🤝 Contributions Welcome!
Whether it's adding new workflow templates, improving hardware detection, or refining the UI, contributions are welcome. See our **[Agent Guidelines](AGENTS.md)** for standards.

---

## 📜 License
Distributed under the **MIT License**. See **[LICENSE](LICENSE)** for more information.

---

## 🌟 Acknowledgments
This work builds upon the foundations (and failures) in:
- [JARVISv1 (Just A Rough Very Incomplete Start)](https://github.com/bentman/JARVISv1)
- [JARVISv2 (Just Almost Real Viable Intelligent System)](https://github.com/bentman/JARVISv2) 
- [JARVISv3 (Just A Reliable Variant In Service)](https://github.com/bentman/JARVISv3)
- [JARVISv4 (Just A Reimagined Version In Stasis)](https://github.com/bentman/JARVISv4)