# Component 1: Backend API - Task Specification

**Status**: Ready for Agent Assignment  
**Priority**: P0 (Foundation)  
**Estimated Time**: 1-2 days  
**Dependencies**: None

---

## Objective

Create a FastAPI backend server with a `/chat` endpoint that accepts user messages and returns responses. Initial implementation will echo the message back (LLM integration in Component 2).

---

## Files to Create

1. **backend/main.py** - FastAPI application with endpoints
2. **backend/models.py** - Pydantic request/response schemas
3. **backend/requirements.txt** - Python dependencies
4. **backend/Dockerfile** - Container image for backend
5. **tests/test_backend.py** - Backend API tests
6. **docker-compose.yml** - Service orchestration (backend only for now)

---

## Requirements

### 1. FastAPI Application (backend/main.py)

**Endpoints**:
- `GET /health` - Health check endpoint
  - Returns: `{"status": "healthy", "timestamp": "<ISO 8601>"}`
  
- `POST /chat` - Chat endpoint
  - Accepts: `ChatRequest` (see models)
  - Returns: `ChatResponse` (see models)
  - Behavior: Echo back the user message with conversation ID

**CORS Configuration**:
- Allow origins: `["http://localhost:3000"]` (frontend dev server)
- Allow methods: `["GET", "POST"]`
- Allow headers: `["*"]`

**Error Handling**:
- 422 for validation errors
- 500 for server errors
- Include error details in response

### 2. Pydantic Models (backend/models.py)

**ChatRequest**:
```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
```

**ChatResponse**:
```python
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str  # ISO 8601 format
```

### 3. Dependencies (backend/requirements.txt)

Required packages:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
python-multipart==0.0.6
pytest==7.4.4
httpx==0.26.0
```

### 4. Dockerfile (backend/Dockerfile)

**Requirements**:
- Base image: `python:3.11-slim`
- Working directory: `/app`
- Copy requirements.txt and install dependencies
- Copy application code
- Expose port 8000
- Command: `uvicorn main:app --host 0.0.0.0 --port 8000`

### 5. Docker Compose (docker-compose.yml)

**Services**:
- `backend`:
  - Build from `./backend`
  - Ports: `8000:8000`
  - Volumes: 
    - `./backend:/app` (for development)
    - `./data:/data` (for future database)
    - `./models:/models` (for future LLM)
  - Environment: Load from `.env` if present
  - Restart: unless-stopped

---

## Test Criteria (tests/test_backend.py)

**Required Tests**:

1. **test_health_endpoint**:
   - GET /health returns 200
   - Response has "status" and "timestamp" fields
   - Status value is "healthy"

2. **test_chat_endpoint_basic**:
   - POST /chat with valid message returns 200
   - Response has "response", "conversation_id", "timestamp"
   - Response echoes the input message

3. **test_chat_endpoint_with_conversation_id**:
   - POST /chat with existing conversation_id
   - Response returns same conversation_id

4. **test_chat_endpoint_invalid_request**:
   - POST /chat with empty message returns 422
   - POST /chat with missing message returns 422

5. **test_cors_headers**:
   - OPTIONS request returns appropriate CORS headers

---

## Implementation Details

### Echo Response Logic (backend/main.py)

For Component 1, the chat endpoint should:
1. Accept user message
2. Generate conversation_id if not provided (use UUID)
3. Echo back message as: "Echo: {user_message}"
4. Include timestamp in ISO 8601 format
5. Return response

**Example**:
```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Component 1: Simple echo (LLM in Component 2)
    response_text = f"Echo: {request.message}"
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        timestamp=timestamp
    )
```

---

## Success Criteria

**Unit Tests**:
- [ ] All tests in `tests/test_backend.py` pass
- [ ] Test coverage ≥ 80% for backend code
- [ ] No failing tests

**Manual Validation**:
- [ ] `docker compose up` starts backend without errors
- [ ] `curl http://localhost:8000/health` returns healthy status
- [ ] `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"test"}'` returns echo response
- [ ] Backend logs show no errors

**Integration Readiness**:
- [ ] Backend API is ready for Component 2 (LLM integration)
- [ ] Docker setup is ready for Component 3 (Frontend)

---

## Constraints

**Must Follow**:
- ✅ No legacy code references (no v1/v2/v3/v4)
- ✅ Simple implementation (no over-engineering)
- ✅ All tests pass before completion
- ✅ Code is readable with clear comments
- ✅ Follow Project.md specifications exactly

**Must NOT**:
- ❌ Add LLM integration (that's Component 2)
- ❌ Add database operations (that's Component 4)
- ❌ Add tool execution (that's Component 5)
- ❌ Add features not in specification
- ❌ Skip tests or validation

---

## Validation Steps

After implementation, agent must execute:

```bash
# 1. Run tests
cd /home/claude/JARVISv5
pytest tests/test_backend.py -v

# 2. Build Docker image
docker compose build backend

# 3. Start backend service
docker compose up backend -d

# 4. Test health endpoint
curl http://localhost:8000/health

# 5. Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, JARVIS"}'

# 6. Check logs
docker compose logs backend

# 7. Stop service
docker compose down
```

All commands must succeed with expected output.

---

## Evidence Required

Agent must provide:

```markdown
## Component 1: Backend API - Completion Report

**Files Created**:
- backend/main.py (XXX lines)
- backend/models.py (YYY lines)
- backend/requirements.txt (ZZZ lines)
- backend/Dockerfile (AAA lines)
- docker-compose.yml (BBB lines)
- tests/test_backend.py (CCC lines)

**Test Results**:
```bash
pytest tests/test_backend.py -v
```
[Full test output showing all PASSED]

**Docker Build**:
```bash
docker compose build backend
```
[Build success output]

**Service Startup**:
```bash
docker compose up backend -d
docker compose ps
```
[Container running status]

**Health Check**:
```bash
curl http://localhost:8000/health
```
[JSON response]

**Chat Endpoint**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```
[JSON response with echo]

**Status**: ✅ COMPLETE

**Blockers**: None

**Next Steps**: Ready for Component 2 (LLM Integration)
```

---

## Notes for Agent

- This is a **foundation component** - keep it simple
- Focus on **correct structure** and **passing tests**
- Echo response is **intentional** - LLM comes in Component 2
- Docker setup should be **reusable** for future components
- Code should be **easy to understand** for next agent

---

## Estimated Timeline

- **Setup & Understanding**: 30 minutes
- **Implementation**: 2-3 hours
- **Testing**: 1-2 hours
- **Docker Setup**: 1 hour
- **Validation & Documentation**: 1 hour

**Total**: 1 day for experienced agent

---

**Ready for agent assignment.**
