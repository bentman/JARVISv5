# AGENTS.md: Agent Collaboration Rules for JARVISv5

> **Purpose**: Define how agents work on JARVISv5 to prevent confusion, sprawl, and incomplete work
> **Last Updated**: 2026-02-07

---

## Core Principle

**One agent, one task, one deliverable, clear evidence of success**

Agents work on **isolated, testable, verifiable tasks** with **no coordination required**.

---

## The Rules (NON-NEGOTIABLE)

### Rule 1: Single Source of Truth

**Project.md defines WHAT to build**
- Read Project.md before starting any task
- Follow specifications exactly
- Do NOT add features not in Project.md
- Do NOT defer features that ARE in Project.md

**AGENTS.md (this file) defines HOW to work**
- Follow workflow exactly
- No shortcuts
- No assumptions
- Evidence required

### Rule 2: No Legacy References

**Do NOT**:
- ❌ Look at JARVISv1/v2/v3/v4 code
- ❌ Port code from previous versions
- ❌ Reference old patterns or architecture
- ❌ Copy file structures from legacy repos
- ❌ Import legacy libraries or dependencies

**Why**: Legacy references cause agent confusion and import technical debt

**DO**:
- ✅ Read Project.md for specifications
- ✅ Implement from scratch based on requirements
- ✅ Use standard libraries and patterns
- ✅ Create clean, simple code

### Rule 3: Test-First Development

**Workflow** (must follow this order):

1. **Read Task Specification** - Understand requirements completely
2. **Write Test First** - Create `tests/test_[component].py` with expected behavior
3. **Write Implementation** - Create component code to make tests pass
4. **Run Tests** - Execute `pytest tests/test_[component].py`
5. **Fix Until Pass** - If tests fail, debug and fix (no user intervention)
6. **Provide Evidence** - Show test output proving success
7. **Integration Test** - Verify component works with existing system
8. **Done** - Only when all tests pass

**No "I implemented X"** - only **"Tests pass for X (evidence: ...)"**

### Rule 4: Single-File Tasks

**Good Task Structure**:
- Creates 1 primary file (e.g., `backend/llm.py`)
- Creates 1 test file (e.g., `tests/test_llm.py`)
- Clear, specific requirements
- Independently testable
- No dependencies on other in-progress work

**Bad Task Structure**:
- "Implement memory system" (too broad, multiple files)
- "Integrate frontend and backend" (too vague, coordination required)
- "Fix bugs" (no clear scope or test criteria)

**Task Complexity Limit**:
- ≤ 200 lines of implementation code
- ≤ 100 lines of test code
- Completable in one work session
- No multi-day tasks

### Rule 5: Evidence Required

Every task completion must include:

```markdown
## Task: [Component Name]

**Files Created**:
- /path/to/implementation.py (XXX lines)
- /path/to/test_implementation.py (YYY lines)

**Tests Executed**:
```bash
pytest tests/test_implementation.py -v
```

**Test Results**:
```
test_function_name_1 PASSED
test_function_name_2 PASSED
test_function_name_3 PASSED

=== 3 passed in 0.5s ===
```

**Integration Validation**:
[Describe how component integrates, show manual test if applicable]

**Status**: ✅ COMPLETE
```

**No evidence = incomplete task**

### Rule 6: No Scope Creep

**Stay within task boundaries**:
- Build only what's specified
- Don't add "helpful" features
- Don't optimize prematurely
- Don't refactor unrelated code

**If you notice something that could be improved**:
- ✅ Note it in task completion comments
- ✅ Suggest as separate future task
- ❌ Don't implement it now

### Rule 7: Simple > Perfect

**Prefer**:
- ✅ Simple, readable code
- ✅ Minimal dependencies
- ✅ Standard patterns
- ✅ Clear variable names
- ✅ Inline comments for complex logic

**Avoid**:
- ❌ Clever abstractions
- ❌ Premature optimization
- ❌ Excessive modularity
- ❌ Design patterns unless necessary
- ❌ Over-engineering

**Measure**: "Can another agent understand this in 5 minutes?"

---

## Agent Workflow (Step-by-Step)

### Step 1: Task Assignment

**User provides**:
- Task name
- Component to build
- Specific requirements
- Success criteria

**Agent confirms**:
- "I understand I need to build [X]"
- "Requirements: [list]"
- "I will create [files]"
- "Success = [criteria]"

### Step 2: Write Tests

**Agent creates** `tests/test_[component].py`:

```python
import pytest
from backend.component import ComponentClass

def test_component_basic_functionality():
    """Test the core behavior"""
    component = ComponentClass()
    result = component.do_something()
    assert result == expected_value

def test_component_error_handling():
    """Test error cases"""
    component = ComponentClass()
    with pytest.raises(ValueError):
        component.do_something_invalid()

# More tests as needed
```

**Requirements**:
- Cover core functionality
- Test error cases
- Use clear test names
- Include docstrings

### Step 3: Write Implementation

**Agent creates implementation file**:

```python
"""
Component Name: Brief description

Purpose: Why this component exists
Dependencies: What it requires
"""

class ComponentClass:
    """Component description"""
    
    def __init__(self, config: dict = None):
        """Initialize component"""
        self.config = config or {}
    
    def do_something(self) -> str:
        """
        Do the main thing this component does
        
        Returns:
            Result of operation
        """
        # Implementation
        return result
```

**Requirements**:
- Docstrings for module, class, methods
- Type hints where helpful
- Error handling
- Simple, clear logic

### Step 4: Run Tests

**Agent executes**:
```bash
pytest tests/test_[component].py -v
```

**Expected Output**:
```
tests/test_component.py::test_component_basic_functionality PASSED
tests/test_component.py::test_component_error_handling PASSED

=== 2 passed in 0.3s ===
```

**If tests fail**:
1. Read error output
2. Identify issue
3. Fix code
4. Rerun tests
5. Repeat until all pass

**Do NOT** ask user for help unless tests fail after 3 fix attempts

### Step 5: Integration Validation

**Agent verifies component works with existing system**:

For backend components:
```bash
# Start backend
uvicorn backend.main:app --reload

# Test endpoint
curl http://localhost:8000/[endpoint]
```

For frontend components:
```bash
# Start frontend
npm run dev

# Manual test: Open browser, verify behavior
```

For integration:
```bash
# Run integration tests
pytest tests/test_integration.py -v
```

### Step 6: Provide Evidence

**Agent reports**:
- Files created (with line counts)
- Test execution output
- Integration validation results
- Status: COMPLETE or BLOCKED

**If BLOCKED**:
- Describe specific issue
- Show error messages
- Explain attempts made
- Request guidance

### Step 7: Done

**Task is complete when**:
1. ✅ All unit tests pass
2. ✅ Integration validation succeeds
3. ✅ Evidence provided
4. ✅ Code committed/documented

**User approves** and assigns next task

---

## Component Build Order (Phase 1)

Agents work on components **in this exact order**:

1. **Backend API** (Week 1)
   - File: `backend/main.py`
   - Test: `tests/test_backend.py`
   - Depends on: Nothing
   
2. **LLM Integration** (Week 1-2)
   - File: `backend/llm.py`
   - Test: `tests/test_llm.py`
   - Depends on: Backend API
   
3. **Frontend UI** (Week 2)
   - Files: `frontend/src/App.jsx`, `frontend/src/api.js`
   - Test: Manual browser test
   - Depends on: Backend API, LLM Integration
   
4. **Memory Persistence** (Week 3)
   - File: `backend/memory.py`
   - Test: `tests/test_memory.py`
   - Depends on: Backend API
   
5. **Tool Execution** (Week 4)
   - File: `backend/tools.py`
   - Test: `tests/test_tools.py`
   - Depends on: Backend API, LLM Integration

**Do NOT skip order**. Component N+1 depends on Component N working.

---

## What Agents Do

✅ **Read specifications** - Understand requirements from Project.md
✅ **Write tests first** - Define expected behavior
✅ **Implement to spec** - Build what's specified, no more
✅ **Run tests** - Verify functionality
✅ **Fix bugs** - Debug until tests pass
✅ **Provide evidence** - Show proof of success
✅ **Stay focused** - One task at a time
✅ **Ask for clarification** - If requirements unclear

---

## What Agents DON'T Do

❌ **Reference legacy code** - No v1/v2/v3/v4 lookups
❌ **Port from previous versions** - Always implement fresh
❌ **Add features** - Build only what's specified
❌ **Skip tests** - Tests are mandatory
❌ **Coordinate with other agents** - Tasks are independent
❌ **Make architectural decisions** - Follow Project.md
❌ **Modify specifications** - Suggest changes, don't implement
❌ **Assume anything works** - Test everything
❌ **Over-engineer** - Simple solutions preferred

---

## Common Failure Patterns (AVOID THESE)

### ❌ Pattern 1: "I looked at v2 for reference"
**Why Bad**: Imports legacy confusion and technical debt
**Correct**: Read Project.md requirements, implement from scratch

### ❌ Pattern 2: "I added some extra features while I was there"
**Why Bad**: Scope creep, untested functionality
**Correct**: Build only what's specified

### ❌ Pattern 3: "The tests are failing but the code looks right"
**Why Bad**: Unvalidated assumptions
**Correct**: Fix until tests pass, no exceptions

### ❌ Pattern 4: "I'll integrate with the frontend later"
**Why Bad**: Deferred integration causes accumulating issues
**Correct**: Validate integration immediately after implementation

### ❌ Pattern 5: "I refactored the existing code to be cleaner"
**Why Bad**: Unrelated changes, untested modifications
**Correct**: Only touch files specified in task

---

## Success Metrics

**Good Agent Performance**:
- ✅ Tasks completed in 1-2 sessions
- ✅ All tests pass on first submission
- ✅ Clear evidence provided
- ✅ No scope creep
- ✅ Code is simple and readable
- ✅ Integration validated
- ✅ No legacy references

**Poor Agent Performance**:
- ❌ Tasks take multiple days
- ❌ Tests fail repeatedly
- ❌ No clear evidence
- ❌ Added unspecified features
- ❌ Complex, hard-to-read code
- ❌ Integration not tested
- ❌ Referenced v2/v4 code

---

## Task Template (For User to Provide)

When assigning tasks to agents, use this format:

```markdown
## Task: [Component Name]

**Objective**: [One sentence description]

**Files to Create**:
- [path/to/file.py] - [purpose]
- [path/to/test_file.py] - [test coverage]

**Requirements**:
1. [Specific requirement 1]
2. [Specific requirement 2]
3. [Specific requirement 3]

**Dependencies**: [List of required components/libraries]

**Test Criteria**:
- [ ] [Test case 1]
- [ ] [Test case 2]
- [ ] [Test case 3]

**Success Criteria**:
- All tests pass
- Integration with [component] validated
- Evidence provided

**Constraints**:
- No legacy references
- No feature additions
- Keep it simple
- Must complete in 1-2 sessions
```

---

## Emergency Procedures

### If Agent Gets Stuck (After 3 Attempts)

**Agent should**:
1. Document exact error
2. Show all attempts made
3. Request specific guidance
4. Do NOT proceed without resolution

**User will**:
1. Review error and attempts
2. Provide specific fix OR
3. Simplify task scope OR
4. Reassign to different agent

### If Requirements Are Unclear

**Agent should**:
1. Ask specific clarifying questions
2. Do NOT assume or guess
3. Wait for user confirmation
4. Proceed only after clarity

### If Tests Keep Failing

**Agent should**:
1. Show test output
2. Show code implementation
3. Explain fix attempts
4. Request review after 3 failures

**Do NOT** proceed with failing tests

---

## Notes for Future Agents

This AGENTS.md file establishes the **working discipline** for JARVISv5.

Follow these rules strictly to:
- Avoid legacy confusion (no v2/v4 references)
- Prevent scope creep (build only what's specified)
- Ensure quality (tests must pass)
- Enable progress (evidence-gated milestones)

**If you're an agent reading this**: Your job is to build clean, tested, working components. Nothing more, nothing less.

**Trust the process**. Simple, testable, incremental progress wins.
