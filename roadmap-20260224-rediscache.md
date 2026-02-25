# JARVISv5 Redis Caching Integration - Milestone 6

**Status**: PLANNED - Not yet implemented  
**Objective**: Implement Redis-backed caching for frequent queries and context snippets to improve responsiveness and reduce redundant computation.

---

## Current Repository State

### What Already Exists ✅
- **Redis Infrastructure**: `docker-compose.yml` defines `redis` service
- **Redis Dependency**: `backend/requirements.txt` includes `redis` and `hiredis`
- **Environment Variable**: `REDIS_URL=redis://redis:6379/0` in docker-compose.yml
- **Target Integration Points**: 
  - `backend/workflow/nodes/context_builder_node.py` (reconstructs messages each call)
  - `backend/tools/executor.py` (centralizes tool execution)

### What Does NOT Exist Yet ❌
- **`backend/cache/` package**: Does not exist yet
- **Cache configuration in `backend/config/settings.py`**: No cache fields present
- **Cache API endpoints**: Only `/health`, `/task`, `/task/{task_id}` exist currently
- **Cache metrics collection**: No metrics infrastructure
- **File modification tracking**: No invalidation hooks for file-backed tools

---

## Architecture Overview

```
User Query
  ↓
Cache Check (Redis)
  ↓
[HIT] → Return Cached Result (track metric)
  ↓
[MISS] → Compute Result → Cache Result → Return (track metric)
  ↓
Fail-Safe: If Redis unavailable, skip cache (log warning, continue)
```

**Core Principle**: Cache is an optimization, not a dependency. System must work without Redis.

---

## Why Redis for JARVISv5

### Current State
- **Redis service**: Already running in docker-compose.yml
- **Connection**: Backend has REDIS_URL environment variable configured
- **Status**: Infrastructure ready, caching logic not implemented

### Benefits
1. **Reduced Latency**: Fast in-memory lookups vs database queries
2. **Lower Compute**: Avoid re-embedding same semantic queries
3. **Scalability**: Handles concurrent access efficiently
4. **Observability**: Built-in metrics for cache performance

### Use Cases
1. **Context Builder**: Cache recent message context by task_id
2. **Semantic Search**: Cache embedding results for repeated queries
3. **LLM Prompts**: Cache assembled prompts for similar inputs
4. **Tool Results**: Cache deterministic tool outputs (read_file for same path)

---

## Cache Strategy

### What to Cache

| Data Type | Key Pattern | TTL | Invalidation |
|-----------|-------------|-----|--------------|
| **Context snippets** | `context:{task_id}:{turn}` | 1 hour | On new message |
| **Semantic embeddings** | `embed:{hash(text)}` | 24 hours | Never (deterministic) |
| **Tool results** | `tool:{tool_name}:{hash(params)}` | 30 minutes | On file modification |
| **LLM prompts** | `prompt:{hash(context)}` | 1 hour | Manual |

### What NOT to Cache

- **Episodic traces**: Append-only, no benefit
- **Working state**: Frequently mutated
- **Model outputs**: Non-deterministic (temperature > 0)
- **User credentials**: Security risk

---

## Implementation Tasks

### Task 6.1: Redis Client Wrapper with Fail-Safe

**File**: `backend/cache/redis_client.py` (NEW)

**Purpose**: Connection management with automatic fallback when Redis unavailable.

**Implementation**:

```python
"""
Redis client wrapper for JARVISv5 caching with fail-safe behavior.
"""
from __future__ import annotations

import json
from typing import Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCacheClient:
    """Redis client with fail-safe fallback behavior."""
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        enabled: bool = True,
        default_ttl: int = 3600
    ):
        """
        Initialize Redis client.
        
        Args:
            url: Redis connection URL
            enabled: Whether caching is enabled
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self.default_ttl = default_ttl
        self.client: redis.Redis | None = None
        self._connection_failed = False
        
        if self.enabled:
            try:
                self.client = redis.from_url(
                    url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.client.ping()
            except Exception as exc:
                self._connection_failed = True
                self.client = None
                print(f"[WARN] Redis connection failed: {exc}")
                print("[WARN] Caching disabled, using fallback")
    
    def get(self, key: str) -> str | None:
        """
        Get value from cache.
        
        Returns None on miss or error (fail-safe).
        """
        if not self.enabled or self._connection_failed or not self.client:
            return None
        
        try:
            return self.client.get(key)
        except Exception as exc:
            print(f"[WARN] Redis GET error for key '{key}': {exc}")
            return None
    
    def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Returns True if successful, False otherwise (fail-safe).
        """
        if not self.enabled or self._connection_failed or not self.client:
            return False
        
        try:
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            self.client.setex(key, ttl_seconds, value)
            return True
        except Exception as exc:
            print(f"[WARN] Redis SET error for key '{key}': {exc}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.enabled or self._connection_failed or not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Returns count of deleted keys.
        """
        if not self.enabled or self._connection_failed or not self.client:
            return 0
        
        try:
            keys = list(self.client.scan_iter(match=pattern))
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception:
            return 0
    
    def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value from cache."""
        value = self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    
    def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | None = None
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_str = json.dumps(value, separators=(',', ':'))
            return self.set(key, json_str, ttl)
        except TypeError:
            return False
    
    def health_check(self) -> dict[str, Any]:
        """Check Redis connection health."""
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "message": "Caching disabled"
            }
        
        if self._connection_failed:
            return {
                "enabled": True,
                "connected": False,
                "message": "Connection failed, using fallback"
            }
        
        try:
            if self.client:
                self.client.ping()
                info = self.client.info('stats')
                return {
                    "enabled": True,
                    "connected": True,
                    "hits": info.get('keyspace_hits', 0),
                    "misses": info.get('keyspace_misses', 0),
                    "message": "Connected"
                }
        except Exception as exc:
            return {
                "enabled": True,
                "connected": False,
                "message": f"Health check failed: {exc}"
            }
        
        return {"enabled": True, "connected": False, "message": "Unknown state"}


def create_default_redis_client() -> RedisCacheClient:
    """Create Redis client with environment-based configuration."""
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
    
    return RedisCacheClient(
        url=redis_url,
        enabled=cache_enabled,
        default_ttl=default_ttl
    )
```

**Test**: `tests/unit/test_redis_client.py` (NEW)

```python
"""
Unit tests for Redis cache client
"""
from pathlib import Path

import pytest

from backend.cache.redis_client import RedisCacheClient


@pytest.fixture
def redis_client():
    """Create test Redis client using DB 1 for isolation"""
    client = RedisCacheClient(
        url="redis://localhost:6379/1",
        enabled=True,
        default_ttl=60
    )
    yield client
    # Cleanup
    if client.client:
        client.client.flushdb()


def test_set_and_get(redis_client: RedisCacheClient) -> None:
    """Test basic set and get"""
    success = redis_client.set("test:key", "test_value")
    assert success is True
    
    value = redis_client.get("test:key")
    assert value == "test_value"


def test_get_miss_returns_none(redis_client: RedisCacheClient) -> None:
    """Test cache miss returns None"""
    value = redis_client.get("nonexistent:key")
    assert value is None


def test_json_set_and_get(redis_client: RedisCacheClient) -> None:
    """Test JSON serialization"""
    data = {"foo": "bar", "count": 42}
    
    success = redis_client.set_json("test:json", data)
    assert success is True
    
    retrieved = redis_client.get_json("test:json")
    assert retrieved == data


def test_fail_safe_on_connection_error() -> None:
    """Test fail-safe behavior when Redis unavailable"""
    client = RedisCacheClient(url="redis://invalid:9999/0", enabled=True)
    
    # Should not raise, should return None/False
    value = client.get("any:key")
    assert value is None
    
    success = client.set("any:key", "value")
    assert success is False
```

**Validation** (per AGENTS contract):
```bash
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_redis_client.py -v
```

---

### Task 6.2: Cache Key Generator

**File**: `backend/cache/key_generator.py` (NEW)

**Purpose**: Deterministic cache key generation with hashing for complex inputs.

**Implementation**:

```python
"""
Cache key generation utilities.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def generate_context_key(task_id: str, turn: int) -> str:
    """
    Generate cache key for context snippet.
    
    Args:
        task_id: Task identifier
        turn: Message turn number
    
    Returns:
        Cache key like "context:task-abc123:5"
    """
    return f"context:{task_id}:{turn}"


def generate_embedding_key(text: str) -> str:
    """
    Generate cache key for semantic embedding.
    
    Args:
        text: Text to embed
    
    Returns:
        Cache key like "embed:a1b2c3d4..."
    """
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    return f"embed:{text_hash}"


def generate_tool_key(tool_name: str, params: dict[str, Any]) -> str:
    """
    Generate cache key for tool result.
    
    Args:
        tool_name: Name of tool
        params: Tool parameters
    
    Returns:
        Cache key like "tool:read_file:a1b2c3d4..."
    """
    # Deterministic JSON serialization
    params_json = json.dumps(params, sort_keys=True, separators=(',', ':'))
    params_hash = hashlib.sha256(params_json.encode('utf-8')).hexdigest()[:16]
    return f"tool:{tool_name}:{params_hash}"


def generate_prompt_key(context_hash: str) -> str:
    """
    Generate cache key for assembled prompt.
    
    Args:
        context_hash: Hash of context used in prompt
    
    Returns:
        Cache key like "prompt:a1b2c3d4..."
    """
    return f"prompt:{context_hash}"


def hash_dict(data: dict[str, Any]) -> str:
    """
    Generate deterministic hash of dictionary.
    
    Args:
        data: Dictionary to hash
    
    Returns:
        First 16 chars of SHA256 hex digest
    """
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
```

**Test**: `tests/unit/test_key_generator.py`

```python
"""
Unit tests for cache key generator
"""
from backend.cache.key_generator import (
    generate_context_key,
    generate_embedding_key,
    generate_tool_key,
    hash_dict
)


def test_context_key_format():
    """Test context key format"""
    key = generate_context_key("task-abc123", 5)
    assert key == "context:task-abc123:5"


def test_embedding_key_deterministic():
    """Test embedding key is deterministic"""
    text = "Hello, world!"
    key1 = generate_embedding_key(text)
    key2 = generate_embedding_key(text)
    
    assert key1 == key2
    assert key1.startswith("embed:")


def test_tool_key_deterministic():
    """Test tool key is deterministic for same params"""
    params = {"path": "file.txt", "encoding": "utf-8"}
    
    key1 = generate_tool_key("read_file", params)
    key2 = generate_tool_key("read_file", params)
    
    assert key1 == key2
    assert key1.startswith("tool:read_file:")


def test_tool_key_different_param_order():
    """Test tool key same regardless of param order"""
    params1 = {"path": "file.txt", "encoding": "utf-8"}
    params2 = {"encoding": "utf-8", "path": "file.txt"}
    
    key1 = generate_tool_key("read_file", params1)
    key2 = generate_tool_key("read_file", params2)
    
    assert key1 == key2


def test_hash_dict_deterministic():
    """Test dictionary hashing is deterministic"""
    data = {"b": 2, "a": 1, "c": 3}
    
    hash1 = hash_dict(data)
    hash2 = hash_dict(data)
    
    assert hash1 == hash2
    assert len(hash1) == 16
```

---

### Task 6.3: Cache Metrics Collector

**File**: `backend/cache/metrics.py` (NEW)

**Note**: In-memory singleton is fine for dev/single-worker. For multi-worker production, metrics should aggregate in Redis itself.

**Implementation**:

```python
"""
Cache metrics collection and reporting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    # Per-category breakdowns
    category_hits: dict[str, int] = field(default_factory=dict)
    category_misses: dict[str, int] = field(default_factory=dict)
    
    def record_hit(self, category: str = "general") -> None:
        """Record cache hit."""
        self.hits += 1
        self.category_hits[category] = self.category_hits.get(category, 0) + 1
    
    def record_miss(self, category: str = "general") -> None:
        """Record cache miss."""
        self.misses += 1
        self.category_misses[category] = self.category_misses.get(category, 0) + 1
    
    def record_set(self) -> None:
        """Record cache set operation."""
        self.sets += 1
    
    def record_delete(self) -> None:
        """Record cache delete operation."""
        self.deletes += 1
    
    def record_error(self) -> None:
        """Record cache error."""
        self.errors += 1
    
    def hit_rate(self) -> float:
        """
        Calculate overall hit rate.
        
        Returns 0.0 if no requests made.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total
    
    def category_hit_rate(self, category: str) -> float:
        """Calculate hit rate for specific category."""
        hits = self.category_hits.get(category, 0)
        misses = self.category_misses.get(category, 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        return hits / total
    
    def summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_requests": self.hits + self.misses,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate():.2%}",
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "categories": {
                cat: {
                    "hits": self.category_hits.get(cat, 0),
                    "misses": self.category_misses.get(cat, 0),
                    "hit_rate": f"{self.category_hit_rate(cat):.2%}"
                }
                for cat in set(self.category_hits.keys()) | set(self.category_misses.keys())
            }
        }
    
    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.category_hits.clear()
        self.category_misses.clear()


# Global metrics instance
_global_metrics = CacheMetrics()


def get_metrics() -> CacheMetrics:
    """Get global cache metrics instance."""
    return _global_metrics
```

---

### Task 6.4: Cached Context Builder

**File**: `backend/workflow/nodes/context_builder_node.py` (modifications)

**Purpose**: Add caching to context builder for repeated queries.

**Implementation**:

```python
# At top of file
from backend.cache.redis_client import RedisCacheClient
from backend.cache.key_generator import generate_context_key
from backend.cache.metrics import get_metrics


class ContextBuilderNode(BaseNode):
    def __init__(self, cache_client: RedisCacheClient | None = None):
        """
        Initialize context builder with optional cache.
        
        Args:
            cache_client: Optional Redis cache client. If None, no caching.
        """
        self.cache = cache_client
        self.metrics = get_metrics() if cache_client else None
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task_id = context.get("task_id")
        turn = context.get("turn", 0)
        
        # Try cache first if available
        if self.cache and task_id:
            cache_key = generate_context_key(task_id, turn)
            cached = self.cache.get_json(cache_key)
            
            if cached:
                if self.metrics:
                    self.metrics.record_hit("context")
                context["messages"] = cached.get("messages", [])
                context["cache_hit"] = True
                return context
            
            if self.metrics:
                self.metrics.record_miss("context")
        
        # Cache miss - compute context
        # ... existing context building logic ...
        
        messages = context.get("messages", [])
        
        # Cache result if cache available
        if self.cache and task_id and messages:
            cache_key = generate_context_key(task_id, turn)
            self.cache.set_json(cache_key, {"messages": messages}, ttl=3600)
            if self.metrics:
                self.metrics.record_set()
        
        context["cache_hit"] = False
        return context
```

**Test Update**: `tests/unit/test_nodes.py` (ADD cache test)

```python
def test_context_builder_with_cache(tmp_path: Path) -> None:
    """Test context builder uses cache when available"""
    from backend.cache.redis_client import RedisCacheClient
    
    cache = RedisCacheClient(url="redis://localhost:6379/1", enabled=True)
    node = ContextBuilderNode(cache_client=cache)
    
    context = {
        "task_id": "test-task",
        "turn": 1,
        "messages": []
    }
    
    # First call - cache miss
    result1 = node.execute(context)
    assert result1.get("cache_hit") is False
    
    # Second call - cache hit
    result2 = node.execute(context)
    assert result2.get("cache_hit") is True
    
    # Cleanup
    if cache.client:
        cache.client.flushdb()
```

---

### Task 6.5: Tool Executor Integration

**File**: `backend/tools/executor.py` (MODIFY)

**Critical**: Preserve backward compatibility. Cache must be optional parameter.

**Stale Read Mitigation**: For file tools, include file mtime in cache key OR use shorter TTL.

**Implementation**:
```python
def execute_tool_call(
    request: ToolExecutionRequest,
    registry: ToolRegistry,
    sandbox: Sandbox,
    dispatch_map: dict[str, ToolDispatchHandler],
    cache_client: RedisCacheClient | None = None,  # NEW optional parameter
    enable_caching: bool = True  # NEW optional parameter
) -> tuple[bool, dict[str, Any]]:
    """
    Execute tool with optional caching.
    
    Args:
        request: Tool execution request
        registry: Tool registry
        sandbox: Sandbox instance
        dispatch_map: Tool dispatch map
        cache_client: Optional Redis cache client (default: None, no caching)
        enable_caching: Whether to use cache if available (default: True)
    
    Returns:
        (success, result_dict)
    """
    
    tool = registry.get(request.tool_name)
    if not tool:
        return False, {
            "code": "tool_not_found",
            "tool_name": request.tool_name,
            "message": f"Tool not found: {request.tool_name}",
        }
    
    # Only cache READ_ONLY tools
    cacheable = (
        enable_caching and
        cache_client is not None and
        tool.permission_tier == PermissionTier.READ_ONLY
    )
    
    # Check cache
    if cacheable:
        from backend.cache.key_generator import generate_tool_key
        from backend.cache.metrics import get_metrics
        
        cache_key = generate_tool_key(request.tool_name, request.payload)
        cached = cache_client.get_json(cache_key)
        
        if cached:
            get_metrics().record_hit("tool")
            cached["cache_hit"] = True
            return True, cached
        
        get_metrics().record_miss("tool")
    
    # Validate and execute (EXISTING LOGIC - unchanged)
    validated_ok, validated_payload_or_error = registry.validate_input(
        request.tool_name, request.payload
    )
    if not validated_ok:
        return False, validated_payload_or_error
    
    # Permission checks (EXISTING LOGIC - unchanged)
    # ... existing permission checks ...
    
    handler = dispatch_map.get(request.tool_name)
    if handler is None:
        return False, {
            "code": "tool_not_implemented",
            "tool_name": request.tool_name,
            "message": f"Tool handler not implemented: {request.tool_name}",
        }
    
    try:
        ok, result = handler(sandbox, validated_payload_or_error)
    except Exception as exc:
        return False, {
            "code": "execution_error",
            "tool_name": request.tool_name,
            "message": f"Tool execution failed: {exc}",
        }
    
    # Cache successful READ_ONLY results
    if cacheable and ok:
        # NOTE: For file tools, shorter TTL mitigates stale reads
        ttl = 1800  # 30 minutes
        cache_client.set_json(cache_key, result, ttl=ttl)
        get_metrics().record_set()
    
    result["cache_hit"] = False
    return ok, result
```

**Test Update**: Add cache tests to `tests/unit/test_tool_executor.py`

```python
def test_tool_executor_caching_read_only(tmp_path: Path) -> None:
    """Test tool executor caches READ_ONLY tool results"""
    from backend.cache.redis_client import RedisCacheClient
    
    # Setup
    root = tmp_path / "root"
    root.mkdir()
    test_file = root / "test.txt"
    test_file.write_text("Hello")
    
    registry, sandbox = _build_registry_and_sandbox(root)
    cache = RedisCacheClient(url="redis://localhost:6379/1", enabled=True)
    
    # First call - cache miss
    ok1, result1 = execute_tool_call(
        ToolExecutionRequest(tool_name="read_file", payload={"path": str(test_file)}),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
        cache_client=cache
    )
    
    assert ok1 is True
    assert result1.get("cache_hit") is False
    
    # Second call - cache hit
    ok2, result2 = execute_tool_call(
        ToolExecutionRequest(tool_name="read_file", payload={"path": str(test_file)}),
        registry,
        sandbox,
        build_file_tool_dispatch_map(),
        cache_client=cache
    )
    
    assert ok2 is True
    assert result2.get("cache_hit") is True
    
    # Cleanup
    if cache.client:
        cache.client.flushdb()
```

---

### Task 6.6: Configuration

**File**: `backend/config/settings.py` (MODIFY)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ... EXISTING fields (unchanged) ...
    
    # Cache Configuration (NEW)
    CACHE_ENABLED: bool = True
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_DEFAULT_TTL: int = 3600
    CACHE_TTL_CONTEXT: int = 3600
    CACHE_TTL_TOOL: int = 1800
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**File**: `.env` (if exists) & `.env.example` (MODIFY - add cache section)

```bash
# Existing sections...

# Redis Cache Configuration
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=3600
CACHE_TTL_CONTEXT=3600
CACHE_TTL_TOOL=1800
```

---

### Task 6.7: API Endpoints (Optional)

**File**: `backend/api/main.py` (MODIFY)

**Security Note**: Invalidation endpoint should be protected (not implemented in this milestone).

```python
from backend.cache.redis_client import create_default_redis_client
from backend.cache.metrics import get_metrics

# Initialize cache at module level
cache_client = create_default_redis_client()


@app.get("/cache/health")
def cache_health():
    """Get cache connection health status."""
    return cache_client.health_check()


@app.get("/cache/metrics")
def cache_metrics():
    """Get cache performance metrics."""
    return get_metrics().summary()


# NOTE: Invalidation endpoint deferred - requires auth/rate-limiting
# @app.post("/cache/invalidate")  # DO NOT IMPLEMENT without auth
```

---

## File Modification Tracking (Deferred)

**Problem**: Caching `read_file` by params only can return stale data if file changes.

**Mitigation Strategies** (choose one for future enhancement):

1. **Include mtime in cache key** (requires file stat on every request - defeats purpose)
2. **Shorter TTL for file tools** (30 min - implemented above)
3. **File watcher with invalidation** (complex, deferred to post-M6)
4. **User-initiated invalidation** (manual, requires protected endpoint)

**For Milestone 6**: Use short TTL (30 min) as adequate mitigation.

---

## Summary of Deliverables

### New Files
1. `backend/cache/__init__.py`
2. `backend/cache/redis_client.py`
3. `backend/cache/key_generator.py`
4. `backend/cache/metrics.py`
5. `tests/unit/test_redis_client.py`
6. `tests/unit/test_key_generator.py`

### Modified Files
1. `backend/workflow/nodes/context_builder_node.py` - Add optional cache parameter
2. `backend/tools/executor.py` - Add optional cache parameters (preserve backward compat)
3. `backend/config/settings.py` - Add cache configuration fields
4. `.env.example` - Add cache environment variables
5. `backend/api/main.py` - Add cache health/metrics endpoints (invalidation deferred)
6. `tests/unit/test_nodes.py` - Add cache tests
7. `tests/unit/test_tool_executor.py` - Add cache tests

---

## Validation Commands (Per AGENTS Contract)

```bash
# Ensure Redis is running
docker compose up -d redis

# Test Redis connection
docker compose exec redis redis-cli ping
# Expected: PONG

# Unit tests (use backend venv Python)
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_redis_client.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_key_generator.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_nodes.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_tool_executor.py -v

# Full validation harness
.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit

# Integration test (manual)
.\backend\.venv\Scripts\python.exe -c "
from backend.cache.redis_client import create_default_redis_client

client = create_default_redis_client()
print(f'Cache enabled: {client.enabled}')
print(f'Health: {client.health_check()}')
"
```

---

## Known Limitations & Future Work

### Limitations in Milestone 6
1. **Stale file reads**: 30-min TTL mitigates but doesn't eliminate
2. **No file watcher**: Manual invalidation only
3. **In-memory metrics**: Fragments across workers in production
4. **No cache invalidation API**: Deferred (requires auth)
5. **No automated cache warming**: Cold start each deploy

### Post-Milestone 6 Enhancements
1. File modification tracking with inotify/watchdog
2. Redis-backed metrics aggregation
3. Protected invalidation API with rate limiting
4. Cache warming on startup for common queries
5. TTL tuning based on observed hit rates

---

## Fail-Safe Guarantees

1. ✅ **Redis unavailable**: System works (logs warning, skips cache)
2. ✅ **Cache corruption**: Returns None, recomputes
3. ✅ **Network timeout**: 2-second timeout, falls back
4. ✅ **Import error**: Works without redis package installed
5. ✅ **Backward compatible**: All cache parameters optional with defaults

**Cache is an optimization, not a dependency.**

---

## CHANGE_LOG Entry Format (After Implementation)

```
- 2026-02-XX HH:MM
  - Summary: Completed Milestone 6 Redis caching integration with fail-safe behavior and backward-compatible API surface.
  - Scope: `backend/cache/redis_client.py`, `backend/cache/key_generator.py`, `backend/cache/metrics.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/tools/executor.py`, `backend/config/settings.py`, `.env.example`, `backend/api/main.py`, `tests/unit/test_redis_client.py`, `tests/unit/test_key_generator.py`, `tests/unit/test_nodes.py`, `tests/unit/test_tool_executor.py`.
  - Key behaviors:
    - Fail-safe fallback when Redis unavailable (no errors, logs warning).
    - Backward-compatible: All cache parameters optional with None defaults.
    - Context caching: 1-hour TTL, keyed by task_id + turn.
    - Tool result caching: 30-minute TTL, READ_ONLY tools only.
    - Cache health/metrics endpoints: GET /cache/health, GET /cache/metrics.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_redis_client.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
```