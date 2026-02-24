# JARVISv5 Redis Caching Integration - Milestone 6

**Objective**: Implement Redis-backed caching for frequent queries and context snippets to improve responsiveness and reduce redundant computation.

---

## Architecture Overview

```
User Query
  ↓
Cache Check (Redis)
  ↓
[HIT] → Return Cached Result
  ↓
[MISS] → Compute Result → Cache Result → Return
  ↓
Observability: Log cache hit/miss metrics
```

**Core Principle**: Cache frequently accessed data with configurable TTL and fail-safe fallback.

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

### Task 6.1: Redis Client Wrapper

**File**: `backend/cache/redis_client.py`

**Purpose**: Centralized Redis connection management with fail-safe fallback.

**Implementation**:

```python
"""
Redis client wrapper for JARVISv5 caching.
"""
from __future__ import annotations

import json
from typing import Any

import redis


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
        self.enabled = enabled
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
            except (redis.ConnectionError, redis.TimeoutError) as exc:
                self._connection_failed = True
                self.client = None
                print(f"[WARN] Redis connection failed: {exc}")
                print("[WARN] Caching disabled, falling back to direct computation")
    
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
        except Exception as exc:
            print(f"[WARN] Redis DELETE error for key '{key}': {exc}")
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
        except Exception as exc:
            print(f"[WARN] Redis pattern invalidation error for '{pattern}': {exc}")
            return 0
    
    def get_json(self, key: str) -> dict[str, Any] | None:
        """Get JSON value from cache."""
        value = self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            print(f"[WARN] Invalid JSON in cache key '{key}': {exc}")
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
        except TypeError as exc:
            print(f"[WARN] Cannot serialize to JSON for key '{key}': {exc}")
            return False
    
    def health_check(self) -> dict[str, Any]:
        """
        Check Redis connection health.
        
        Returns status dict with connection info.
        """
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
        
        return {
            "enabled": True,
            "connected": False,
            "message": "Unknown state"
        }


def create_default_redis_client() -> RedisCacheClient:
    """Create Redis client with default configuration."""
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

**Test**: `tests/unit/test_redis_client.py`

```python
"""
Unit tests for Redis cache client
"""
import pytest
from backend.cache.redis_client import RedisCacheClient


@pytest.fixture
def redis_client():
    """Create test Redis client"""
    client = RedisCacheClient(
        url="redis://localhost:6379/1",  # Use DB 1 for tests
        enabled=True,
        default_ttl=60
    )
    yield client
    # Cleanup
    if client.client:
        client.client.flushdb()


def test_set_and_get(redis_client):
    """Test basic set and get"""
    success = redis_client.set("test:key", "test_value")
    assert success is True
    
    value = redis_client.get("test:key")
    assert value == "test_value"


def test_get_miss_returns_none(redis_client):
    """Test cache miss returns None"""
    value = redis_client.get("nonexistent:key")
    assert value is None


def test_json_set_and_get(redis_client):
    """Test JSON serialization"""
    data = {"foo": "bar", "count": 42}
    
    success = redis_client.set_json("test:json", data)
    assert success is True
    
    retrieved = redis_client.get_json("test:json")
    assert retrieved == data


def test_invalidate_pattern(redis_client):
    """Test pattern-based invalidation"""
    redis_client.set("context:task1:1", "data1")
    redis_client.set("context:task1:2", "data2")
    redis_client.set("context:task2:1", "data3")
    
    deleted = redis_client.invalidate_pattern("context:task1:*")
    assert deleted == 2
    
    assert redis_client.get("context:task1:1") is None
    assert redis_client.get("context:task2:1") == "data3"


def test_fail_safe_on_connection_error():
    """Test fail-safe behavior when Redis unavailable"""
    client = RedisCacheClient(url="redis://invalid:9999/0", enabled=True)
    
    # Should not raise, should return None/False
    value = client.get("any:key")
    assert value is None
    
    success = client.set("any:key", "value")
    assert success is False
```

**Validation**:
```bash
# Ensure Redis is running
docker compose up -d redis

# Run tests
pytest tests/unit/test_redis_client.py -v
```

---

### Task 6.2: Cache Key Generator

**File**: `backend/cache/key_generator.py`

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

**File**: `backend/cache/metrics.py`

**Purpose**: Track cache hit/miss rates for observability.

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
# Add to imports
from backend.cache.redis_client import create_default_redis_client
from backend.cache.key_generator import generate_context_key
from backend.cache.metrics import get_metrics

class ContextBuilderNode(BaseNode):
    def __init__(self, cache_client=None):
        # Initialize cache client
        self.cache = cache_client or create_default_redis_client()
        self.metrics = get_metrics()
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        task_id = context.get("task_id")
        turn = context.get("turn", 0)
        
        # Try cache first
        if task_id:
            cache_key = generate_context_key(task_id, turn)
            cached = self.cache.get_json(cache_key)
            
            if cached:
                self.metrics.record_hit("context")
                context["messages"] = cached.get("messages", [])
                context["cache_hit"] = True
                return context
            
            self.metrics.record_miss("context")
        
        # Cache miss - compute context
        # ... existing context building logic ...
        
        messages = context.get("messages", [])
        
        # Cache result
        if task_id and messages:
            cache_key = generate_context_key(task_id, turn)
            self.cache.set_json(
                cache_key,
                {"messages": messages},
                ttl=3600  # 1 hour
            )
            self.metrics.record_set()
        
        context["cache_hit"] = False
        return context
```

---

### Task 6.5: Cached Tool Results

**File**: `backend/tools/executor.py` (modifications)

**Purpose**: Cache deterministic tool results (e.g., read_file).

**Implementation**:

```python
# Add to execute_tool_call function

def execute_tool_call(
    request: ToolExecutionRequest,
    registry: ToolRegistry,
    sandbox: Sandbox,
    dispatch_map: dict[str, ToolDispatchHandler],
    cache_client: RedisCacheClient | None = None,
    enable_caching: bool = True
) -> tuple[bool, dict[str, Any]]:
    """Execute tool with optional caching."""
    
    tool = registry.get(request.tool_name)
    if not tool:
        return False, {"code": "tool_not_found", "tool_name": request.tool_name}
    
    # Only cache READ_ONLY tools
    cacheable = (
        enable_caching and
        cache_client and
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
    
    # Execute tool (existing logic)
    # ... validation and execution ...
    
    ok, result = handler(sandbox, validated_payload_or_error)
    
    # Cache successful READ_ONLY results
    if cacheable and ok:
        cache_client.set_json(
            cache_key,
            result,
            ttl=1800  # 30 minutes
        )
        get_metrics().record_set()
    
    result["cache_hit"] = False
    return ok, result
```

---

### Task 6.6: Health Check Endpoint

**File**: `backend/api/main.py` (additions)

**Purpose**: Add cache health and metrics to API.

**Implementation**:

```python
from backend.cache.redis_client import create_default_redis_client
from backend.cache.metrics import get_metrics

cache_client = create_default_redis_client()

@app.get("/cache/health")
def cache_health():
    """Get cache health status."""
    return cache_client.health_check()


@app.get("/cache/metrics")
def cache_metrics():
    """Get cache performance metrics."""
    return get_metrics().summary()


@app.post("/cache/invalidate")
def cache_invalidate(pattern: str):
    """Invalidate cache keys matching pattern."""
    deleted = cache_client.invalidate_pattern(pattern)
    return {"deleted": deleted, "pattern": pattern}
```

---

## Configuration

### Environment Variables

**Update `.env.example`**:

```bash
# Redis Cache Configuration
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
CACHE_DEFAULT_TTL=3600  # 1 hour in seconds

# Cache TTL per category (seconds)
CACHE_TTL_CONTEXT=3600      # 1 hour
CACHE_TTL_EMBEDDING=86400   # 24 hours
CACHE_TTL_TOOL=1800         # 30 minutes
CACHE_TTL_PROMPT=3600       # 1 hour
```

**Update `backend/config/settings.py`**:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Cache Configuration
    CACHE_ENABLED: bool = True
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_DEFAULT_TTL: int = 3600
    CACHE_TTL_CONTEXT: int = 3600
    CACHE_TTL_EMBEDDING: int = 86400
    CACHE_TTL_TOOL: int = 1800
    CACHE_TTL_PROMPT: int = 3600
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

---

## Summary of Deliverables

### Created Files

1. **`backend/cache/redis_client.py`** - Redis client with fail-safe fallback
2. **`backend/cache/key_generator.py`** - Deterministic cache key generation
3. **`backend/cache/metrics.py`** - Cache performance metrics
4. **`backend/cache/__init__.py`** - Package initialization
5. **`tests/unit/test_redis_client.py`** - Redis client tests
6. **`tests/unit/test_key_generator.py`** - Key generator tests
7. **`tests/unit/test_cache_metrics.py`** - Metrics tests

### Modified Files

- `backend/workflow/nodes/context_builder_node.py` - Add caching
- `backend/tools/executor.py` - Cache tool results
- `backend/api/main.py` - Add cache endpoints
- `backend/config/settings.py` - Cache configuration
- `.env.example` - Cache environment variables

---

## Cache Features

| Feature | Status | Description |
|---------|--------|-------------|
| Redis Client | ✅ Implemented | Connection management with fail-safe |
| Key Generation | ✅ Implemented | Deterministic hashing for cache keys |
| Metrics Collection | ✅ Implemented | Hit/miss rates by category |
| Context Caching | ✅ Implemented | Cache message context by task/turn |
| Tool Result Caching | ✅ Implemented | Cache READ_ONLY tool outputs |
| Health Check | ✅ Implemented | API endpoint for cache status |
| Invalidation | ✅ Implemented | Pattern-based cache clearing |

---

## Validation Commands

```bash
# Ensure Redis is running
docker compose up -d redis

# Test Redis connection
docker compose exec redis redis-cli ping
# Expected: PONG

# Unit tests
pytest tests/unit/test_redis_client.py -v
pytest tests/unit/test_key_generator.py -v
pytest tests/unit/test_cache_metrics.py -v

# Integration test
python -c "
from backend.cache.redis_client import create_default_redis_client
from backend.cache.key_generator import generate_context_key
from backend.cache.metrics import get_metrics

# Create client
client = create_default_redis_client()
print(f'Cache enabled: {client.enabled}')
print(f'Health: {client.health_check()}')

# Test caching
key = generate_context_key('test-task', 1)
client.set_json(key, {'messages': ['Hello']})
cached = client.get_json(key)
print(f'Cached data: {cached}')

# Check metrics
metrics = get_metrics()
print(f'Metrics: {metrics.summary()}')
"

# Full validation
python scripts/validate_backend.py --scope unit

# Check cache endpoints
curl http://localhost:8000/cache/health
curl http://localhost:8000/cache/metrics
```

---

## Cache Policy Guidelines

### TTL Strategy

**Short TTL (30 min - 1 hour)**:
- Context snippets (frequently updated)
- Tool results (may change on disk)
- Assembled prompts (context-dependent)

**Long TTL (24 hours)**:
- Semantic embeddings (deterministic)
- Static tool results (version hashes)

**No Expiration**:
- Never - always use TTL for automatic cleanup

### Invalidation Strategy

**On User Action**:
- New message → Invalidate `context:{task_id}:*`
- File modification → Invalidate `tool:read_file:*`
- Manual clear → Invalidate all via pattern

**Automatic**:
- TTL expiration handles most cases
- No need for complex invalidation logic

---

## Observability

### Metrics to Track

1. **Hit Rate**: `hits / (hits + misses)`
2. **Category Breakdown**: Hit rates per cache category
3. **Set/Delete Rates**: Cache write activity
4. **Error Rate**: Failed operations

### Health Monitoring

```bash
# Check cache health
curl http://localhost:8000/cache/health

# Response:
{
  "enabled": true,
  "connected": true,
  "hits": 1247,
  "misses": 352,
  "message": "Connected"
}

# Check metrics
curl http://localhost:8000/cache/metrics

# Response:
{
  "total_requests": 1599,
  "hits": 1247,
  "misses": 352,
  "hit_rate": "77.99%",
  "sets": 405,
  "deletes": 12,
  "errors": 0,
  "categories": {
    "context": {"hits": 892, "misses": 124, "hit_rate": "87.79%"},
    "tool": {"hits": 355, "misses": 228, "hit_rate": "60.89%"}
  }
}
```

---

## Performance Impact

### Expected Improvements

| Operation | Before Cache | With Cache | Improvement |
|-----------|-------------|------------|-------------|
| Context retrieval | ~50ms | ~2ms | **25x faster** |
| Tool read_file (same path) | ~10ms | ~1ms | **10x faster** |
| Semantic embedding | ~200ms | ~2ms | **100x faster** |

### Memory Usage

- **Redis footprint**: ~10-50MB typical (configurable maxmemory)
- **Key count**: ~1000-10000 keys typical
- **Eviction**: LRU policy when maxmemory reached

---

## Next Steps After Milestone 6

With caching in place:

1. **Monitor hit rates** to tune TTL values
2. **Add semantic embedding caching** (Milestone 7)
3. **Cache LLM prompts** for repeated patterns
4. **Implement cache warming** for common queries

This ensures: **Faster response times and reduced redundant computation across all workflow nodes.**

---

## Fail-Safe Guarantees

1. **Redis unavailable**: System works without caching (degrades gracefully)
2. **Cache corruption**: Returns None, recomputes
3. **Network timeout**: 2-second timeout, falls back
4. **Memory pressure**: Redis LRU eviction handles automatically

**Cache is an optimization, not a dependency.**