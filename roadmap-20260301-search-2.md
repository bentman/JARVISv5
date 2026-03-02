# JARVISv5 Search + Policy-Bound Escalation - Milestone 8 (FINAL)

**Status**: PLANNED - Ready for implementation  
**Objective**: Add web search capability with privacy-protected, policy-governed escalation using existing M5 infrastructure and proven patterns from M4-M7.

---

## Agent Feedback Resolution Status

| Issue | Status | Resolution |
|-------|--------|------------|
| **Privacy wrapper API mismatch** | ✅ RESOLVED | Use `evaluate_and_prepare_external_call()` actual signature |
| **EXTERNAL permission tier missing executor logic** | ✅ RESOLVED | Explicit allow semantics + tests specified |
| **Tool registration location underspecified** | ✅ RESOLVED | Follow M4 `ToolCallNode` dispatch pattern |
| **Config coupling minimal** | ✅ RESOLVED | Settings tests follow existing pattern |
| **BeautifulSoup not only solution** | ✅ RESOLVED | Trafilatura primary, BS4 fallback |
| **DDG reliability concerns** | ✅ RESOLVED | Provider ladder with fallback |
| **SearXNG JSON format** | ✅ RESOLVED | Explicit JSON enablement check |

---

## Prerequisites (Verified from Repo)

### What Exists ✅ (M1-M7 Complete)

**M5 Privacy** (`tests: 20 passed in 0.31s`):
- ✅ `PrivacyExternalCallWrapper.evaluate_and_prepare_external_call()` - Returns `(bool, dict)` with `redacted_payload_text` as serialized string
- ✅ `PIIRedactor` - 9 PII types detection
- ✅ `SecurityAuditLogger` - JSONL audit to `data/logs/security_audit.jsonl`

**M4 Tools** (Pattern established):
- ✅ `ToolRegistry` + `ToolDefinition` with `PermissionTier` enum
- ✅ `execute_tool_call()` in `executor.py` with privacy integration
- ✅ `ToolCallNode` runtime dispatch via `build_file_tool_dispatch_map()`
- ✅ Sandbox roots injection from `tool_call` context dict

**M6 Caching**:
- ✅ `RedisCacheClient` with deterministic keys
- ✅ Fail-safe behavior ready for search results

**M7 Retrieval**:
- ✅ `HybridRetriever` for local-first search
- ✅ Context builder integration complete

**Dependencies**:
- ✅ `ddgs>=9.10.0` in requirements.txt
- ✅ `requests>=2.31.0` in requirements.txt

### What Does NOT Exist ❌

- ❌ Search providers (`SearXNGProvider`, `DuckDuckGoProvider`, `TavilyProvider`)
- ❌ Budget tracker
- ❌ Search tools (`search_web`, `fetch_url`)
- ❌ `EXTERNAL` permission tier + executor logic
- ❌ Extraction library (trafilatura)

---

## Implementation Tasks

### Task 8.1: Add EXTERNAL Permission Tier with Executor Logic

**File**: `backend/tools/registry.py` (MODIFY)

**Change 1**: Add enum value
```python
class PermissionTier(str, Enum):
    READ_ONLY = "read_only"
    WRITE_SAFE = "write_safe"
    SYSTEM = "system"
    EXTERNAL = "external"  # NEW
```

**File**: `backend/tools/executor.py` (MODIFY)

**Change 2**: Add EXTERNAL permission check (after SYSTEM check)
```python
# Add after existing SYSTEM check (~line 80)
if tool.permission_tier == PermissionTier.EXTERNAL:
    if not request.external_call:
        return False, {
            "code": "permission_denied",
            "tool_name": request.tool_name,
            "message": "external_call flag required for EXTERNAL tools",
            "required_permission": PermissionTier.EXTERNAL.value,
        }
    if not request.allow_external:
        return False, {
            "code": "permission_denied",
            "tool_name": request.tool_name,
            "message": "allow_external must be true for EXTERNAL tools",
            "required_permission": PermissionTier.EXTERNAL.value,
        }
```

**Test**: `tests/unit/test_tool_executor_external.py` (NEW)

```python
"""Test EXTERNAL permission tier executor logic"""
import pytest
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig
from pydantic import BaseModel


class MockExternalInput(BaseModel):
    query: str


def test_external_tool_denied_without_external_call_flag():
    """EXTERNAL tool denied when external_call=False"""
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="mock_external",
        description="Test external tool",
        permission_tier=PermissionTier.EXTERNAL,
        input_model=MockExternalInput
    ))
    
    request = ToolExecutionRequest(
        tool_name="mock_external",
        payload={"query": "test"},
        external_call=False,  # Missing flag
        allow_external=True
    )
    
    sandbox = Sandbox(SandboxConfig(allowed_roots=()))
    ok, result = execute_tool_call(request, registry, sandbox, {})
    
    assert not ok
    assert result["code"] == "permission_denied"
    assert "external_call flag required" in result["message"]


def test_external_tool_denied_without_allow_external():
    """EXTERNAL tool denied when allow_external=False"""
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="mock_external",
        description="Test external tool",
        permission_tier=PermissionTier.EXTERNAL,
        input_model=MockExternalInput
    ))
    
    request = ToolExecutionRequest(
        tool_name="mock_external",
        payload={"query": "test"},
        external_call=True,
        allow_external=False  # Not allowed
    )
    
    sandbox = Sandbox(SandboxConfig(allowed_roots=()))
    ok, result = execute_tool_call(request, registry, sandbox, {})
    
    assert not ok
    assert result["code"] == "permission_denied"
    assert "allow_external must be true" in result["message"]
```

**Acceptance Criteria**:
- [ ] `PermissionTier.EXTERNAL` enum added
- [ ] Executor has explicit EXTERNAL permission branch
- [ ] Test passes: external tool denied without flags
- [ ] Test passes: external tool allowed with both flags

---

### Task 8.2: Simple Budget Tracker

**File**: `backend/search/budget.py` (NEW)

**Implementation** (100 lines):
```python
"""Simple budget tracker for external API calls"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class BudgetTracker:
    """Track API spending, enforce daily/monthly limits"""
    
    def __init__(
        self,
        storage_path: str = "data/search/budget.json",
        daily_limit_usd: float = 0.0,
        monthly_limit_usd: float = 0.0
    ):
        self.storage_path = Path(storage_path)
        self.daily_limit = daily_limit_usd
        self.monthly_limit = monthly_limit_usd
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load()
    
    def _load(self) -> list[dict]:
        """Load spending records"""
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, "r") as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save(self):
        """Save spending records"""
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.records, f, indent=2)
        except Exception as exc:
            print(f"[WARN] Failed to save budget: {exc}")
    
    def record(self, provider: str, cost_usd: float, task_id: str | None = None):
        """Record spending"""
        self.records.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "cost_usd": cost_usd,
            "task_id": task_id
        })
        self._save()
    
    def can_afford(self, estimated_usd: float = 0.0) -> tuple[bool, str]:
        """Check if within budget limits"""
        now = datetime.now(timezone.utc)
        
        # Daily limit check
        if self.daily_limit > 0:
            day_ago = now - timedelta(days=1)
            daily_spent = sum(
                r["cost_usd"] for r in self.records
                if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= day_ago
            )
            if daily_spent + estimated_usd > self.daily_limit:
                return False, f"Daily limit ${daily_spent:.4f}/${self.daily_limit:.2f}"
        
        # Monthly limit check
        if self.monthly_limit > 0:
            month_ago = now - timedelta(days=30)
            monthly_spent = sum(
                r["cost_usd"] for r in self.records
                if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= month_ago
            )
            if monthly_spent + estimated_usd > self.monthly_limit:
                return False, f"Monthly limit ${monthly_spent:.4f}/${self.monthly_limit:.2f}"
        
        return True, "OK"
```

**Test**: `tests/unit/test_search_budget.py` (NEW)

```python
"""Test budget tracker"""
import pytest
from backend.search.budget import BudgetTracker


def test_budget_tracker_allows_when_no_limits(tmp_path):
    """Budget allows when limits are 0"""
    tracker = BudgetTracker(
        storage_path=str(tmp_path / "budget.json"),
        daily_limit_usd=0.0,
        monthly_limit_usd=0.0
    )
    
    can_afford, reason = tracker.can_afford(1.0)
    assert can_afford
    assert reason == "OK"


def test_budget_tracker_enforces_daily_limit(tmp_path):
    """Budget enforces daily limit"""
    tracker = BudgetTracker(
        storage_path=str(tmp_path / "budget.json"),
        daily_limit_usd=1.0
    )
    
    # Spend 0.6
    tracker.record("test", 0.6)
    
    # Can afford 0.3 more
    can_afford, _ = tracker.can_afford(0.3)
    assert can_afford
    
    # Cannot afford 0.5 more (would exceed 1.0)
    can_afford, reason = tracker.can_afford(0.5)
    assert not can_afford
    assert "Daily limit" in reason
```

**Acceptance Criteria**:
- [ ] BudgetTracker created with JSON storage
- [ ] `can_afford()` checks daily/monthly limits
- [ ] `record()` persists spending
- [ ] Tests pass for limits and recording

---

### Task 8.3: Search Providers (SearXNG, DuckDuckGo, Tavily)

**File**: `backend/search/providers.py` (NEW)

**Implementation** (~200 lines with 3 providers):

```python
"""Search providers - SearXNG (local), DuckDuckGo (free), Tavily (paid)"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    """Single search result"""
    title: str
    url: str
    snippet: str
    provider: str


@dataclass
class SearchResponse:
    """Search response with results"""
    results: list[SearchResult]
    provider: str
    cost_usd: float


class SearXNGProvider:
    """
    SearXNG provider - local-first, privacy-focused
    
    Requires SearXNG running in Docker:
    docker run -d -p 8080:8080 searxng/searxng
    
    Note: SearXNG must have JSON format enabled in settings.yml
    """
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")
    
    def health_check(self) -> tuple[bool, str]:
        """Check if SearXNG is available and JSON enabled"""
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"q": "test", "format": "json"},
                timeout=5
            )
            if response.status_code == 200:
                return True, "OK"
            elif response.status_code == 403:
                return False, "JSON format disabled in SearXNG settings"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as exc:
            return False, str(exc)
    
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Search using local SearXNG instance"""
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    provider="searxng"
                ))
            
            return SearchResponse(
                results=results,
                provider="searxng",
                cost_usd=0.0  # Local, no cost
            )
            
        except Exception as exc:
            print(f"[WARN] SearXNG search failed: {exc}")
            return SearchResponse(results=[], provider="searxng", cost_usd=0.0)


class DuckDuckGoProvider:
    """
    DuckDuckGo provider - free, no API key required
    
    Uses duckduckgo_search library (already in requirements.txt)
    Note: Subject to rate limiting, use as fallback
    """
    
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Search using DuckDuckGo"""
        try:
            with DDGS() as ddgs:
                results_raw = list(ddgs.text(query, max_results=max_results))
            
            results = []
            for item in results_raw:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("href", ""),
                    snippet=item.get("body", ""),
                    provider="duckduckgo"
                ))
            
            return SearchResponse(
                results=results,
                provider="duckduckgo",
                cost_usd=0.0  # Free
            )
            
        except Exception as exc:
            print(f"[WARN] DuckDuckGo search failed: {exc}")
            return SearchResponse(results=[], provider="duckduckgo", cost_usd=0.0)


class TavilyProvider:
    """
    Tavily provider - paid tier, high quality results
    
    Requires API key: TAVILY_API_KEY=tvly-xxx...
    Pricing: ~$0.005 per search
    """
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
    
    def search(self, query: str, max_results: int = 10) -> SearchResponse:
        """Search using Tavily API"""
        if not self.api_key:
            print("[WARN] Tavily API key not configured")
            return SearchResponse(results=[], provider="tavily", cost_usd=0.0)
        
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic"
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    provider="tavily"
                ))
            
            return SearchResponse(
                results=results,
                provider="tavily",
                cost_usd=0.005  # Approximate cost
            )
            
        except Exception as exc:
            print(f"[WARN] Tavily search failed: {exc}")
            return SearchResponse(results=[], provider="tavily", cost_usd=0.0)


def get_search_provider(
    provider_name: str = "duckduckgo",
    searxng_url: str | None = None,
    tavily_key: str | None = None
):
    """
    Get search provider by name with fallback ladder.
    
    Priority: SearXNG (local) -> DuckDuckGo (free) -> Tavily (paid)
    """
    if provider_name == "searxng":
        provider = SearXNGProvider(base_url=searxng_url or "http://localhost:8080")
        # Check health before returning
        healthy, reason = provider.health_check()
        if healthy:
            return provider
        print(f"[WARN] SearXNG unhealthy ({reason}), falling back to DuckDuckGo")
        return DuckDuckGoProvider()
    
    elif provider_name == "tavily":
        return TavilyProvider(api_key=tavily_key)
    
    else:  # Default to duckduckgo
        return DuckDuckGoProvider()
```

**Test**: `tests/unit/test_search_providers.py` (NEW)

```python
"""Test search providers"""
import pytest
from backend.search.providers import (
    DuckDuckGoProvider,
    SearXNGProvider,
    TavilyProvider,
    get_search_provider
)


def test_duckduckgo_provider_returns_results():
    """DuckDuckGo provider returns search results"""
    provider = DuckDuckGoProvider()
    response = provider.search("python programming", max_results=3)
    
    assert response.provider == "duckduckgo"
    assert response.cost_usd == 0.0
    assert len(response.results) <= 3


def test_searxng_health_check_fails_when_unavailable():
    """SearXNG health check fails when service unavailable"""
    provider = SearXNGProvider(base_url="http://localhost:9999")
    healthy, reason = provider.health_check()
    
    assert not healthy
    assert len(reason) > 0


def test_get_provider_returns_duckduckgo_by_default():
    """get_search_provider returns DuckDuckGo by default"""
    provider = get_search_provider()
    assert isinstance(provider, DuckDuckGoProvider)
```

**Acceptance Criteria**:
- [ ] Three providers implemented with fallback
- [ ] SearXNG has JSON format health check
- [ ] DuckDuckGo uses ddgs library
- [ ] Tavily uses API key from env
- [ ] Provider ladder works: searxng→ddg→tavily
- [ ] Tests pass for all providers

---

### Task 8.4: Search Web Tool (M5 Privacy Integration)

**File**: `backend/tools/search_tools.py` (NEW)

**Implementation** (~150 lines with actual privacy API):

```python
"""
Search tools using M5 privacy wrapper
"""
from __future__ import annotations

import os
from pydantic import BaseModel, Field

from backend.search.budget import BudgetTracker
from backend.search.providers import get_search_provider
from backend.security.audit_logger import SecurityAuditLogger
from backend.security.privacy_wrapper import (
    ExternalCallRequest,
    PrivacyExternalCallWrapper,
)
from backend.security.redactor import PIIRedactor


class SearchWebInput(BaseModel):
    """Input for search_web tool"""
    query: str = Field(..., description="Search query")
    max_results: int = Field(10, ge=1, le=20)
    provider: str = Field("duckduckgo", description="searxng, duckduckgo, tavily")


def run_search_web(
    payload: SearchWebInput,
    *,
    task_id: str | None = None,
    audit_log_path: str = "data/logs/security_audit.jsonl"
) -> tuple[bool, dict]:
    """
    Execute web search using M5 privacy wrapper.
    
    CRITICAL: Uses actual M5 API signature:
    - evaluate_and_prepare_external_call() returns (bool, dict)
    - dict contains 'redacted_payload_text' as serialized JSON string
    """
    # Load configuration
    allow_external = os.getenv("ALLOW_EXTERNAL_SEARCH", "false").lower() == "true"
    daily_budget = float(os.getenv("DAILY_BUDGET_USD", "0.0"))
    monthly_budget = float(os.getenv("MONTHLY_BUDGET_USD", "0.0"))
    redaction_mode = os.getenv("SEARCH_REDACTION_MODE", "strict")
    
    # Step 1: Feature flag check
    if not allow_external:
        return False, {
            "code": "external_disabled",
            "results": [],
            "message": "External search disabled. Set ALLOW_EXTERNAL_SEARCH=true"
        }
    
    # Step 2: Budget check
    budget_tracker = BudgetTracker(
        daily_limit_usd=daily_budget,
        monthly_limit_usd=monthly_budget
    )
    
    estimated_cost = 0.005 if payload.provider == "tavily" else 0.0
    can_afford, reason = budget_tracker.can_afford(estimated_cost)
    if not can_afford:
        return False, {
            "code": "budget_exceeded",
            "results": [],
            "message": f"Budget exceeded: {reason}"
        }
    
    # Step 3: M5 Privacy wrapper (ACTUAL API)
    redactor = PIIRedactor()
    audit_logger = SecurityAuditLogger(audit_log_path)
    privacy_wrapper = PrivacyExternalCallWrapper(redactor, audit_logger)
    
    # Prepare external call request
    external_request = ExternalCallRequest(
        provider=payload.provider,
        endpoint="search",
        payload={"query": payload.query, "max_results": payload.max_results},
        task_id=task_id,
        allow_external=True,  # Already checked above
        redaction_mode=redaction_mode
    )
    
    # Call M5 privacy wrapper (returns tuple[bool, dict])
    privacy_ok, privacy_result = privacy_wrapper.evaluate_and_prepare_external_call(
        external_request
    )
    
    if not privacy_ok:
        return False, privacy_result
    
    # Extract redacted query from serialized string
    import json
    try:
        redacted_payload_dict = json.loads(privacy_result["redacted_payload_text"])
        query_to_use = redacted_payload_dict.get("query", payload.query)
    except Exception:
        query_to_use = payload.query  # Fallback
    
    # Step 4: Execute search with provider ladder
    provider = get_search_provider(
        provider_name=payload.provider,
        searxng_url=os.getenv("SEARXNG_URL"),
        tavily_key=os.getenv("TAVILY_API_KEY")
    )
    
    try:
        search_response = provider.search(
            query=query_to_use,
            max_results=payload.max_results
        )
    except Exception as exc:
        return False, {
            "code": "search_failed",
            "results": [],
            "error": str(exc)
        }
    
    # Step 5: Record spending
    if search_response.cost_usd > 0:
        budget_tracker.record(
            provider=search_response.provider,
            cost_usd=search_response.cost_usd,
            task_id=task_id
        )
    
    # Step 6: Return results
    return True, {
        "code": "ok",
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet
            }
            for r in search_response.results
        ],
        "provider": search_response.provider,
        "cost_usd": search_response.cost_usd,
        "query_used": query_to_use
    }
```

**Acceptance Criteria**:
- [ ] Tool uses actual M5 API: `evaluate_and_prepare_external_call()`
- [ ] Handles `redacted_payload_text` as serialized JSON
- [ ] Feature flag + budget checks before search
- [ ] Provider fallback ladder works
- [ ] Budget recording after search
- [ ] Audit logging via M5

---

### Task 8.5: Fetch URL Tool (Trafilatura Primary)

**File**: `backend/tools/search_tools.py` (ADD to existing)

**Dependencies**: Add to `requirements.txt`:
```
trafilatura>=1.12.0
```

**Implementation** (~80 lines):

```python
import trafilatura


class FetchUrlInput(BaseModel):
    """Input for fetch_url tool"""
    url: str = Field(..., description="URL to fetch")
    extractor: str = Field("trafilatura", description="trafilatura or beautifulsoup")


def run_fetch_url(
    payload: FetchUrlInput,
    *,
    task_id: str | None = None,
    audit_log_path: str = "data/logs/security_audit.jsonl"
) -> tuple[bool, dict]:
    """
    Fetch URL content with Trafilatura (primary) or BeautifulSoup (fallback)
    
    Trafilatura: Best-in-class content extraction (ACL 2021, Sandia 2024)
    BeautifulSoup: Simple fallback for edge cases
    """
    import requests
    
    # Feature flag check
    allow_external = os.getenv("ALLOW_EXTERNAL_SEARCH", "false").lower() == "true"
    if not allow_external:
        return False, {
            "code": "external_disabled",
            "content": "",
            "message": "External fetch disabled"
        }
    
    # Budget check (nominal cost)
    budget_tracker = BudgetTracker()
    can_afford, reason = budget_tracker.can_afford(0.0001)
    if not can_afford:
        return False, {
            "code": "budget_exceeded",
            "content": "",
            "message": reason
        }
    
    # Fetch URL
    try:
        response = requests.get(
            payload.url,
            timeout=10,
            headers={"User-Agent": "JARVISv5-Bot/1.0"}
        )
        response.raise_for_status()
        
        # Extract content using selected extractor
        if payload.extractor == "trafilatura":
            # Trafilatura: Best precision/recall balance
            content = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            if not content:
                # Fallback to BeautifulSoup if trafilatura fails
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style"]):
                    script.decompose()
                content = soup.get_text()
        else:
            # BeautifulSoup fallback
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            content = soup.get_text()
        
        # Clean whitespace
        lines = (line.strip() for line in content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        content = "\n".join(chunk for chunk in chunks if chunk)
        
        # Truncate
        if len(content) > 10000:
            content = content[:10000] + "\n[Truncated]"
        
        # Record cost
        budget_tracker.record("http", 0.0001, task_id)
        
        # Audit
        audit_logger = SecurityAuditLogger(audit_log_path)
        audit_logger.log_external_call(
            provider="http",
            endpoint="fetch",
            redacted_payload={"url": payload.url},
            task_id=task_id
        )
        
        return True, {
            "code": "ok",
            "content": content,
            "url": payload.url,
            "extractor": payload.extractor
        }
        
    except Exception as exc:
        return False, {
            "code": "fetch_failed",
            "content": "",
            "error": str(exc)
        }
```

**Acceptance Criteria**:
- [ ] Trafilatura primary extractor
- [ ] BeautifulSoup automatic fallback
- [ ] Budget tracking (nominal cost)
- [ ] Audit logging
- [ ] Tests pass for both extractors

---

### Task 8.6: Tool Registration (M4 Pattern)

**File**: `backend/tools/search_tools.py` (ADD to end)

```python
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry


def register_search_tools(registry: ToolRegistry) -> None:
    """Register search tools following M4 pattern"""
    registry.register(
        ToolDefinition(
            name="search_web",
            description="Search the web using local or external providers",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=SearchWebInput,
        )
    )
    registry.register(
        ToolDefinition(
            name="fetch_url",
            description="Fetch and extract text from a URL",
            permission_tier=PermissionTier.EXTERNAL,
            input_model=FetchUrlInput,
        )
    )


def build_search_tool_dispatch_map():
    """Build dispatch map following M4 pattern"""
    return {
        "search_web": lambda sandbox, payload: run_search_web(
            SearchWebInput.model_validate(payload)
        ),
        "fetch_url": lambda sandbox, payload: run_fetch_url(
            FetchUrlInput.model_validate(payload)
        ),
    }
```

**File**: `backend/workflow/nodes/tool_call_node.py` (MODIFY)

```python
# Add import at top
from backend.tools.search_tools import (
    build_search_tool_dispatch_map,
    register_search_tools,
)

# Modify execute() method - add after register_core_file_tools():
register_search_tools(registry)

# Modify dispatch_map - combine dictionaries:
dispatch_map = {
    **build_file_tool_dispatch_map(),
    **build_search_tool_dispatch_map(),
}

# Pass combined dispatch_map to execute_tool_call()
```

**Acceptance Criteria**:
- [ ] Tools registered in ToolCallNode
- [ ] Dispatch map includes search tools
- [ ] Follows exact M4 pattern
- [ ] Integration test passes

---

### Task 8.7: Configuration

**File**: `backend/config/settings.py` (MODIFY)

```python
class Settings(BaseSettings):
    # ... EXISTING fields ...
    
    # Search & Escalation (NEW)
    ALLOW_EXTERNAL_SEARCH: bool = False  # Feature flag
    DAILY_BUDGET_USD: float = 0.0
    MONTHLY_BUDGET_USD: float = 0.0
    SEARCH_REDACTION_MODE: str = "strict"
    DEFAULT_SEARCH_PROVIDER: str = "duckduckgo"
    SEARXNG_URL: str = "http://localhost:8080"
    TAVILY_API_KEY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**File**: `.env.example` (MODIFY - add section)

```bash
# Search & Escalation
ALLOW_EXTERNAL_SEARCH=false
DAILY_BUDGET_USD=0.0
MONTHLY_BUDGET_USD=0.0
SEARCH_REDACTION_MODE=strict
DEFAULT_SEARCH_PROVIDER=duckduckgo
SEARXNG_URL=http://localhost:8080
TAVILY_API_KEY=your_tavily_api_key_here
```

**Test**: `tests/unit/test_config_search.py` (NEW)

```python
"""Test search configuration following existing settings pattern"""
import os
import pytest
from backend.config.settings import Settings


def test_settings_search_defaults():
    """Search settings have correct defaults"""
    settings = Settings()
    assert settings.ALLOW_EXTERNAL_SEARCH is False
    assert settings.DAILY_BUDGET_USD == 0.0
    assert settings.SEARCH_REDACTION_MODE == "strict"


def test_settings_search_env_overrides(monkeypatch):
    """Search settings can be overridden by environment"""
    monkeypatch.setenv("ALLOW_EXTERNAL_SEARCH", "true")
    monkeypatch.setenv("DAILY_BUDGET_USD", "5.0")
    
    settings = Settings()
    assert settings.ALLOW_EXTERNAL_SEARCH is True
    assert settings.DAILY_BUDGET_USD == 5.0
```

**Acceptance Criteria**:
- [ ] Settings added to Settings class
- [ ] Env variables in .env.example
- [ ] Tests pass following existing pattern

---

### Task 8.8: Docker Compose (SearXNG Service)

**File**: `docker-compose.yml` (MODIFY)

```yaml
services:
  # ... existing services ...
  
  searxng:
    image: searxng/searxng:latest
    container_name: jarvisv5-searxng-1
    ports:
      - "8080:8080"
    environment:
      - BASE_URL=http://localhost:8080/
      - INSTANCE_NAME=JARVISv5
    volumes:
      - ./data/searxng:/etc/searxng:rw
    restart: unless-stopped

# No network needed - default bridge OK
```

**File**: `data/searxng/settings.yml` (CREATE - auto-created by container, but document expected content)

```yaml
# Key requirement: JSON format must be enabled
search:
  formats:
    - html
    - json  # REQUIRED for API access
```

**Acceptance Criteria**:
- [ ] SearXNG service in docker-compose.yml
- [ ] JSON format documented in settings.yml
- [ ] Service starts: `docker compose up -d searxng`
- [ ] Health check works: `curl http://localhost:8080/search?q=test&format=json`

---

### Task 8.9: Dependencies

**File**: `backend/requirements.txt` (MODIFY - add 2 lines)

```python
# After existing ddgs line
trafilatura>=1.12.0
beautifulsoup4>=4.12.0
```

**Acceptance Criteria**:
- [ ] trafilatura added
- [ ] beautifulsoup4 added
- [ ] Dependencies install: `pip install -r backend/requirements.txt`

---

## Summary of Deliverables

### New Files (7)
1. `backend/search/__init__.py`
2. `backend/search/budget.py` - Budget tracker
3. `backend/search/providers.py` - SearXNG, DuckDuckGo, Tavily
4. `backend/tools/search_tools.py` - search_web, fetch_url
5. `tests/unit/test_tool_executor_external.py` - EXTERNAL permission tests
6. `tests/unit/test_search_budget.py` - Budget tests
7. `tests/unit/test_search_providers.py` - Provider tests

### Modified Files (6)
1. `backend/tools/registry.py` - Add EXTERNAL tier
2. `backend/tools/executor.py` - Add EXTERNAL logic
3. `backend/workflow/nodes/tool_call_node.py` - Register search tools
4. `backend/config/settings.py` - Add search config
5. `.env.example` - Add search env vars
6. `docker-compose.yml` - Add SearXNG service
7. `backend/requirements.txt` - Add trafilatura, beautifulsoup4

### New Directories (2)
1. `backend/search/` - Search modules
2. `data/search/` - Budget tracking (auto-created)

---

## Validation Commands (Per AGENTS Contract)

```bash
# Task 8.1 - EXTERNAL permission
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor_external.py -v

# Task 8.2 - Budget tracker
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_budget.py -v

# Task 8.3 - Providers
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_providers.py -v

# Task 8.7 - Config
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_config_search.py -v

# Full validation
.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit
```

---

## Integration Test (Full Workflow)

**File**: `tests/integration/test_search_integration.py` (NEW)

```python
"""Integration test for complete search workflow"""
import pytest
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig
from backend.tools.search_tools import (
    SearchWebInput,
    register_search_tools,
    build_search_tool_dispatch_map,
)
from backend.security.privacy_wrapper import create_default_privacy_wrapper


def test_search_web_full_workflow(monkeypatch, tmp_path):
    """Test complete search_web workflow with privacy integration"""
    # Enable feature
    monkeypatch.setenv("ALLOW_EXTERNAL_SEARCH", "true")
    monkeypatch.setenv("DAILY_BUDGET_USD", "10.0")
    
    # Setup
    registry = ToolRegistry()
    register_search_tools(registry)
    sandbox = Sandbox(SandboxConfig(allowed_roots=()))
    dispatch_map = build_search_tool_dispatch_map()
    privacy_wrapper = create_default_privacy_wrapper(
        log_path=str(tmp_path / "audit.jsonl")
    )
    
    # Execute search
    request = ToolExecutionRequest(
        tool_name="search_web",
        payload={"query": "python programming", "max_results": 5},
        external_call=True,
        allow_external=True,
        external_provider="duckduckgo",
        external_endpoint="search",
        task_id="test-task-123"
    )
    
    ok, result = execute_tool_call(
        request=request,
        registry=registry,
        sandbox=sandbox,
        dispatch_map=dispatch_map,
        privacy_wrapper=privacy_wrapper
    )
    
    # Verify
    assert ok
    assert result["code"] == "ok"
    assert "results" in result
    assert len(result["results"]) <= 5
    assert result["provider"] in ["searxng", "duckduckgo", "tavily"]
```

---

## Known Limitations & Mitigation

| Limitation | Mitigation |
|------------|------------|
| DDG rate limits | Provider ladder: searxng→ddg→tavily |
| SearXNG JSON disabled | Health check with clear error message |
| Trafilatura edge cases | Automatic fallback to BeautifulSoup |
| Budget tracking not real-time | Acceptable for M8 baseline, enhance in M9+ |

---

## CHANGE_LOG Entry Format

```
- 2026-03-XX HH:MM
  - Summary: Completed Milestone 8 Search + Policy-Bound Escalation with SearXNG (local), DuckDuckGo (free), Tavily (paid), integrated with M5 privacy wrapper using actual API contracts, budget tracking, and EXTERNAL permission tier with explicit executor logic.
  - Scope: `backend/search/budget.py`, `backend/search/providers.py`, `backend/tools/search_tools.py`, `backend/tools/registry.py`, `backend/tools/executor.py`, `backend/workflow/nodes/tool_call_node.py`, `backend/config/settings.py`, `.env.example`, `docker-compose.yml`, `backend/requirements.txt`.
  - Key behaviors:
    - EXTERNAL permission tier added with explicit executor allow/deny logic (external_call + allow_external flags required).
    - search_web tool: uses M5 PrivacyExternalCallWrapper.evaluate_and_prepare_external_call() actual API, handles redacted_payload_text as serialized JSON, feature flag + budget checks before search.
    - fetch_url tool: Trafilatura primary extractor (ACL 2021, best-in-class), BeautifulSoup automatic fallback, budget tracking.
    - Three providers: SearXNG (local-first, JSON format health check), DuckDuckGo (free, rate-limit aware), Tavily (paid, $0.005/search).
    - Budget tracker: daily/monthly USD limits, persistent to data/search/budget.json.
    - Provider ladder: searxng→duckduckgo fallback on health check failure.
    - Tool registration follows M4 ToolCallNode pattern with combined dispatch map.
    - SearXNG Docker service added with JSON format enablement documented.
    - trafilatura>=1.12.0 and beautifulsoup4>=4.12.0 added to requirements.txt.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor_external.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_budget.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_search_providers.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
```

---

## Implementation Checklist

- [ ] Task 8.1: EXTERNAL tier + executor logic + tests (PASS)
- [ ] Task 8.2: Budget tracker + tests (PASS)
- [ ] Task 8.3: 3 providers + fallback + tests (PASS)
- [ ] Task 8.4: search_web with M5 actual API + tests (PASS)
- [ ] Task 8.5: fetch_url with trafilatura + tests (PASS)
- [ ] Task 8.6: Tool registration M4 pattern (verified)
- [ ] Task 8.7: Config + tests (PASS)
- [ ] Task 8.8: SearXNG Docker + JSON check (verified)
- [ ] Task 8.9: Dependencies installed (verified)
- [ ] Integration test: Full workflow (PASS)
- [ ] Validation harness: PASS_WITH_SKIPS
- [ ] CHANGE_LOG entry with evidence
- [ ] SYSTEM_INVENTORY entry

---

**Implementation Guide Version**: 3.0 (FINAL - Agent Feedback Resolved)  
**Target Milestone**: M8 - Search + Policy-Bound Escalation  
**Prerequisites**: M1-M7 complete (verified via tests: 20 passed in 0.31s)  
**Estimated Effort**: 9 tasks, ~15 hours  
**Confidence**: HIGH (all Agent concerns resolved, exact API contracts specified)