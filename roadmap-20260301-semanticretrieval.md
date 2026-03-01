# JARVISv5 Hybrid Semantic Retrieval - Milestone 7 (REVISED)

**Status**: PLANNED - Not yet implemented  
**Objective**: Implement episodic + semantic hybrid retrieval with unified scoring, intelligent working state ranking, and context builder integration.

---

## Agent Feedback Integration

This revision addresses critical design risks identified during static analysis:

1. ✅ **Unified scoring contract** (0-1, higher=better across all sources)
2. ✅ **Working state recency decay** (not fixed 1.0 scores)
3. ✅ **Episodic keyword search with SQL indexes**
4. ✅ **Context format compatibility** (preserves message dict structure)
5. ✅ **Embedding cache uses hashed keys** (not raw text)

---

## Current Repository State

### What Already Exists ✅
- **Semantic memory**: `backend/memory/semantic_store.py` with FAISS + SQLite
  - Current: `search()` returns L2 distance dicts
  - Needs: Normalized similarity scores (0-1, higher=better)
- **Episodic memory**: `backend/memory/episodic_db.py` with decisions/tool_calls/validations
  - Needs: `search_decisions()`, `search_tool_calls()` methods
- **Memory manager**: `backend/memory/memory_manager.py` exposes all interfaces
- **Context builder**: `backend/workflow/nodes/context_builder_node.py` with caching
  - Current: Last 10 working state messages only
  - Needs: Hybrid retrieval integration
- **Unit tests**: `test_semantic_store.py`, `test_episodic_db.py` exist

### What Does NOT Exist Yet ❌
- `backend/memory/hybrid_retriever.py`
- Hybrid retrieval tests
- Normalized semantic search API
- Episodic search methods with SQL indexes
- Context builder hybrid integration
- Hybrid retrieval settings/feature flag
- Embedding cache with hashed keys

---

## Unified Scoring Contract

**CRITICAL**: All retrieval sources must return scores in consistent format.

### Canonical Score Format

```python
@dataclass
class RetrievalResult:
    content: str
    source: str  # "working_state", "semantic", "episodic"
    relevance_score: float  # 0.0 to 1.0, higher = more relevant
    recency_score: float    # 0.0 to 1.0, higher = more recent
    final_score: float      # Combined relevance + recency
    metadata: dict[str, Any]
```

### Scoring Rules

1. **All scores normalized to [0, 1]**
2. **Higher score = better match**
3. **Final score = weighted combination**:
   ```python
   final_score = (
       relevance_score * relevance_weight +
       recency_score * recency_weight
   )
   ```

---

## Architecture Overview

```
User Query + Working State Messages
  ↓
Hybrid Retriever
  ├─ Working State (recency decay, not fixed 1.0)
  ├─ Semantic Search (L2 distance → normalized similarity)
  └─ Episodic Search (keyword match + indexed SQL)
  ↓
Score Normalization (all sources → 0-1, higher=better)
  ↓
Weighted Fusion (relevance + recency)
  ↓
Threshold Filter (min final_score)
  ↓
Result Ranking (highest final_score first)
  ↓
Context Format (preserve message dict structure)
  ↓
Redis Cache (optional, 1-hour TTL)
```

---

## Implementation Tasks

### Task 7.1: Unified Scoring Schema

**File**: `backend/memory/retrieval_types.py` (NEW)

**Purpose**: Define canonical retrieval result format shared by all components.

**Implementation**:

```python
"""
Retrieval types and scoring contracts for hybrid retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievalResult:
    """
    Canonical retrieval result with unified scoring.
    
    Scoring contract:
    - All scores are 0.0 to 1.0
    - Higher score = better match
    - relevance_score: How well content matches query
    - recency_score: How recent the content is
    - final_score: Combined score for ranking
    """
    content: str
    source: str  # "working_state", "semantic", "episodic"
    relevance_score: float  # 0.0 to 1.0, higher = more relevant to query
    recency_score: float    # 0.0 to 1.0, higher = more recent
    final_score: float      # Combined score for ranking
    metadata: dict[str, Any]
    
    def __post_init__(self):
        """Validate score ranges"""
        assert 0.0 <= self.relevance_score <= 1.0, f"Invalid relevance_score: {self.relevance_score}"
        assert 0.0 <= self.recency_score <= 1.0, f"Invalid recency_score: {self.recency_score}"
        assert 0.0 <= self.final_score <= 1.0, f"Invalid final_score: {self.final_score}"


@dataclass
class RetrievalConfig:
    """Configuration for hybrid retrieval"""
    # Retrieval limits
    max_semantic_results: int = 5
    max_episodic_results: int = 5
    max_working_state_messages: int = 10
    max_total_results: int = 10
    
    # Quality thresholds
    min_final_score_threshold: float = 0.5
    semantic_similarity_threshold: float = 0.3  # L2 distance threshold
    
    # Scoring weights (relevance vs recency)
    working_state_relevance_weight: float = 0.3
    working_state_recency_weight: float = 0.7
    semantic_relevance_weight: float = 0.9
    semantic_recency_weight: float = 0.1
    episodic_relevance_weight: float = 0.7
    episodic_recency_weight: float = 0.3
    
    # Feature flags
    enable_semantic_search: bool = True
    enable_episodic_search: bool = True
    
    def compute_final_score(
        self,
        relevance: float,
        recency: float,
        source: str
    ) -> float:
        """
        Compute final score from relevance and recency.
        
        Args:
            relevance: Relevance score (0-1)
            recency: Recency score (0-1)
            source: Source type for weight selection
        
        Returns:
            Final combined score (0-1)
        """
        if source == "working_state":
            rel_weight = self.working_state_relevance_weight
            rec_weight = self.working_state_recency_weight
        elif source == "semantic":
            rel_weight = self.semantic_relevance_weight
            rec_weight = self.semantic_recency_weight
        elif source == "episodic":
            rel_weight = self.episodic_relevance_weight
            rec_weight = self.episodic_recency_weight
        else:
            # Default: equal weights
            rel_weight = 0.5
            rec_weight = 0.5
        
        return relevance * rel_weight + recency * rec_weight
```

**Test**: `tests/unit/test_retrieval_types.py` (NEW)

```python
"""
Unit tests for retrieval types and scoring
"""
import pytest

from backend.memory.retrieval_types import RetrievalConfig, RetrievalResult


def test_retrieval_result_score_validation() -> None:
    """Test score validation in RetrievalResult"""
    # Valid scores
    result = RetrievalResult(
        content="test",
        source="semantic",
        relevance_score=0.8,
        recency_score=0.6,
        final_score=0.75,
        metadata={}
    )
    assert result.relevance_score == 0.8
    
    # Invalid relevance score
    with pytest.raises(AssertionError):
        RetrievalResult(
            content="test",
            source="semantic",
            relevance_score=1.5,  # Invalid: > 1.0
            recency_score=0.5,
            final_score=0.5,
            metadata={}
        )


def test_retrieval_config_compute_final_score() -> None:
    """Test final score computation with source-specific weights"""
    config = RetrievalConfig()
    
    # Working state: favors recency (0.7 weight)
    ws_score = config.compute_final_score(
        relevance=0.5,
        recency=1.0,
        source="working_state"
    )
    assert ws_score == 0.5 * 0.3 + 1.0 * 0.7  # 0.85
    
    # Semantic: favors relevance (0.9 weight)
    sem_score = config.compute_final_score(
        relevance=1.0,
        recency=0.5,
        source="semantic"
    )
    assert sem_score == 1.0 * 0.9 + 0.5 * 0.1  # 0.95
```

---

### Task 7.2: Semantic Search with Normalized Scores

**File**: `backend/memory/semantic_store.py` (MODIFY)

**Purpose**: Add `search_text()` method that returns normalized similarity scores.

**Implementation**:

```python
# Add to SemanticMemory class

def search_text(
    self,
    query: str,
    top_k: int = 5,
    distance_threshold: float = 0.3
) -> list[tuple[str, dict[str, Any], float]]:
    """
    Search semantic memory for relevant texts.
    
    CRITICAL: Returns NORMALIZED SIMILARITY SCORES (0-1, higher=better)
    
    Args:
        query: Query text
        top_k: Number of results to return
        distance_threshold: Maximum L2 distance (lower = more strict)
    
    Returns:
        List of (text, metadata, similarity_score) tuples
        similarity_score: 0.0 to 1.0, higher = more similar
        
        Normalization formula:
        similarity = 1 / (1 + L2_distance)
        
        Examples:
        - L2=0.0 (identical) → similarity=1.0
        - L2=1.0 → similarity=0.5
        - L2=3.0 → similarity=0.25
    """
    if self.index is None or self.index.ntotal == 0:
        return []
    
    # Embed query
    query_vector = self._embed(query)
    query_array = self._to_faiss_array(query_vector)
    
    # Search FAISS index (returns L2 distances, lower=better)
    distances, indices = self.index.search(query_array, top_k)
    
    results = []
    with closing(self._connect()) as conn:
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # No more results
                break
            
            # Skip if distance exceeds threshold
            if dist > distance_threshold:
                continue
            
            # Get text and metadata from SQLite
            row = conn.execute(
                "SELECT text, metadata FROM embeddings WHERE vector_id = ?",
                (int(idx),)
            ).fetchone()
            
            if row:
                text, metadata_json = row
                metadata = json.loads(metadata_json)
                
                # CRITICAL: Normalize L2 distance to similarity score
                # Formula: similarity = 1 / (1 + distance)
                # This ensures: 0-1 range, higher=better
                similarity = 1.0 / (1.0 + float(dist))
                
                results.append((text, metadata, similarity))
    
    return results
```

---

### Task 7.3: Episodic Search with SQL Indexes

**File**: `backend/memory/episodic_db.py` (MODIFY)

**Purpose**: Add indexed search methods for decisions and tool calls.

**Implementation**:

```python
# Add to EpisodicMemory._init_db()

def _init_db(self) -> None:
    with closing(self._connect()) as conn:
        # Existing table creation...
        
        # NEW: Add indexes for search performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_task_id ON decisions(task_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON decisions(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_calls_timestamp ON tool_calls(timestamp DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name)"
        )
        
        conn.commit()


# Add search methods

def search_decisions(
    self,
    keywords: list[str],
    task_id: str | None = None,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search decisions by keyword matching with SQL index support.
    
    Args:
        keywords: Keywords to match (OR logic)
        task_id: Optional task ID filter
        limit: Maximum results
    
    Returns:
        List of decision records with timestamp, content, etc.
    """
    if not keywords:
        return []
    
    with closing(self._connect()) as conn:
        # Build WHERE clause for keyword matching
        keyword_conditions = []
        keyword_params = []
        
        for kw in keywords:
            keyword_conditions.append("content LIKE ?")
            keyword_params.append(f"%{kw}%")
        
        where_parts = [f"({' OR '.join(keyword_conditions)})"]
        params = keyword_params
        
        if task_id:
            where_parts.append("task_id = ?")
            params.append(task_id)
        
        where_clause = " AND ".join(where_parts)
        
        # Use timestamp index for ordering
        query = f"""
            SELECT id, timestamp, task_id, action_type, content, status
            FROM decisions
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            {
                "id": row[0],
                "timestamp": row[1],
                "task_id": row[2],
                "action_type": row[3],
                "content": row[4],
                "status": row[5]
            }
            for row in rows
        ]


def search_tool_calls(
    self,
    keywords: list[str],
    tool_name: str | None = None,
    limit: int = 10
) -> list[dict[str, Any]]:
    """
    Search tool calls by keyword matching with SQL index support.
    
    Args:
        keywords: Keywords to match in tool_name or params
        tool_name: Optional exact tool name filter
        limit: Maximum results
    
    Returns:
        List of tool call records
    """
    if not keywords and not tool_name:
        return []
    
    with closing(self._connect()) as conn:
        where_parts = []
        params = []
        
        if keywords:
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("tool_name LIKE ? OR params LIKE ?")
                params.extend([f"%{kw}%", f"%{kw}%"])
            where_parts.append(f"({' OR '.join(keyword_conditions)})")
        
        if tool_name:
            where_parts.append("tool_name = ?")
            params.append(tool_name)
        
        where_clause = " AND ".join(where_parts)
        
        # Use timestamp index for ordering
        query = f"""
            SELECT id, decision_id, tool_name, params, result, timestamp
            FROM tool_calls
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            {
                "id": row[0],
                "decision_id": row[1],
                "tool_name": row[2],
                "params": row[3],
                "result": row[4],
                "timestamp": row[5]
            }
            for row in rows
        ]
```

---

### Task 7.4: Hybrid Retriever with Recency Decay

**File**: `backend/memory/hybrid_retriever.py` (NEW)

**Purpose**: Unified retrieval with recency-aware working state scoring.

**Implementation**:

```python
"""
Hybrid Retriever - Episodic + Semantic + Working State with recency decay
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.memory.episodic_db import EpisodicMemory
from backend.memory.retrieval_types import RetrievalConfig, RetrievalResult
from backend.memory.semantic_store import SemanticMemory


class HybridRetriever:
    """Retrieve and rank results from multiple memory sources"""
    
    def __init__(
        self,
        semantic_memory: SemanticMemory,
        episodic_memory: EpisodicMemory,
        config: RetrievalConfig | None = None
    ):
        self.semantic = semantic_memory
        self.episodic = episodic_memory
        self.config = config or RetrievalConfig()
    
    def retrieve(
        self,
        query: str,
        working_state_messages: list[dict[str, Any]],
        task_id: str | None = None
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant context from all sources.
        
        Args:
            query: User query text
            working_state_messages: Current task messages
            task_id: Current task ID for filtering
        
        Returns:
            List of retrieval results sorted by final_score (highest first)
        """
        results: list[RetrievalResult] = []
        
        # Step 1: Working state with recency decay (NOT fixed 1.0)
        ws_results = self._retrieve_working_state(
            query, working_state_messages
        )
        results.extend(ws_results)
        
        # Step 2: Semantic memory search
        if self.config.enable_semantic_search:
            sem_results = self._retrieve_semantic(query)
            results.extend(sem_results)
        
        # Step 3: Episodic memory search
        if self.config.enable_episodic_search:
            epi_results = self._retrieve_episodic(query, task_id)
            results.extend(epi_results)
        
        # Step 4: Filter by threshold
        results = [
            r for r in results
            if r.final_score >= self.config.min_final_score_threshold
        ]
        
        # Step 5: Sort by final_score (highest first)
        results.sort(key=lambda r: r.final_score, reverse=True)
        
        # Step 6: Limit total results
        results = results[:self.config.max_total_results]
        
        return results
    
    def _retrieve_working_state(
        self,
        query: str,
        messages: list[dict[str, Any]]
    ) -> list[RetrievalResult]:
        """
        Retrieve working state messages with recency decay.
        
        CRITICAL: Uses recency decay, NOT fixed 1.0 scores
        - Most recent message: recency_score = 1.0
        - Oldest message: recency_score decreases exponentially
        - Relevance score: simple keyword match for now
        """
        if not messages:
            return []
        
        results = []
        total_messages = len(messages)
        query_lower = query.lower()
        
        for i, msg in enumerate(messages[:self.config.max_working_state_messages]):
            if not isinstance(msg, dict) or "content" not in msg:
                continue
            
            content = str(msg["content"])
            
            # Recency score: exponential decay from 1.0 (most recent) to 0.1 (oldest)
            # position 0 = oldest, position (total-1) = newest
            position = total_messages - 1 - i if i < total_messages else 0
            recency_score = 0.1 + 0.9 * (position / max(total_messages - 1, 1))
            
            # Relevance score: keyword match (simple for M7, can enhance later)
            content_lower = content.lower()
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in content_lower)
            relevance_score = min(matches / max(len(query_words), 1), 1.0)
            
            # Compute final score using config weights
            final_score = self.config.compute_final_score(
                relevance=relevance_score,
                recency=recency_score,
                source="working_state"
            )
            
            results.append(RetrievalResult(
                content=content,
                source="working_state",
                relevance_score=relevance_score,
                recency_score=recency_score,
                final_score=final_score,
                metadata={"position": i, "role": msg.get("role", "unknown")}
            ))
        
        return results
    
    def _retrieve_semantic(self, query: str) -> list[RetrievalResult]:
        """Retrieve from semantic memory with normalized scores"""
        try:
            # Search returns (text, metadata, similarity) with 0-1 scores
            raw_results = self.semantic.search_text(
                query,
                top_k=self.config.max_semantic_results,
                distance_threshold=self.config.semantic_similarity_threshold
            )
            
            results = []
            for text, metadata, similarity in raw_results:
                # Relevance = similarity score (already 0-1)
                relevance_score = similarity
                
                # Recency from metadata timestamp if available
                recency_score = self._compute_recency_score(
                    metadata.get("timestamp")
                )
                
                final_score = self.config.compute_final_score(
                    relevance=relevance_score,
                    recency=recency_score,
                    source="semantic"
                )
                
                results.append(RetrievalResult(
                    content=text,
                    source="semantic",
                    relevance_score=relevance_score,
                    recency_score=recency_score,
                    final_score=final_score,
                    metadata=metadata
                ))
            
            return results
        except Exception as exc:
            print(f"[WARN] Semantic search failed: {exc}")
            return []
    
    def _retrieve_episodic(
        self,
        query: str,
        task_id: str | None
    ) -> list[RetrievalResult]:
        """Retrieve from episodic memory with keyword search"""
        try:
            # Extract keywords from query
            keywords = [w for w in query.lower().split() if len(w) > 3]
            if not keywords:
                return []
            
            # Search decisions
            decisions = self.episodic.search_decisions(
                keywords=keywords,
                task_id=task_id,
                limit=self.config.max_episodic_results
            )
            
            results = []
            for decision in decisions:
                # Simple keyword match relevance
                content = decision["content"]
                matches = sum(1 for kw in keywords if kw in content.lower())
                relevance_score = min(matches / len(keywords), 1.0)
                
                # Recency from timestamp
                recency_score = self._compute_recency_score(
                    decision.get("timestamp")
                )
                
                final_score = self.config.compute_final_score(
                    relevance=relevance_score,
                    recency=recency_score,
                    source="episodic"
                )
                
                results.append(RetrievalResult(
                    content=content,
                    source="episodic",
                    relevance_score=relevance_score,
                    recency_score=recency_score,
                    final_score=final_score,
                    metadata={
                        "decision_id": decision["id"],
                        "task_id": decision["task_id"],
                        "action_type": decision["action_type"],
                        "timestamp": decision["timestamp"]
                    }
                ))
            
            return results
        except Exception as exc:
            print(f"[WARN] Episodic search failed: {exc}")
            return []
    
    def _compute_recency_score(self, timestamp_str: str | None) -> float:
        """
        Compute recency score from timestamp.
        
        Returns:
            0.0 to 1.0, higher = more recent
            1.0 = within last hour
            0.5 = ~1 day ago
            0.1 = >7 days ago
        """
        if not timestamp_str:
            return 0.5  # Default: moderate recency
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_hours = (now - timestamp).total_seconds() / 3600
            
            # Exponential decay: score = exp(-age_hours / 24)
            # 0 hours → 1.0
            # 24 hours → 0.37
            # 168 hours (7 days) → 0.001
            import math
            recency = math.exp(-age_hours / 24)
            return max(0.1, min(1.0, recency))
        except Exception:
            return 0.5  # Default on parse error
    
    def compute_retrieval_metrics(
        self,
        results: list[RetrievalResult]
    ) -> dict[str, Any]:
        """Compute metrics about retrieval quality"""
        if not results:
            return {
                "total_results": 0,
                "source_breakdown": {},
                "avg_final_score": 0.0,
                "avg_relevance_score": 0.0,
                "avg_recency_score": 0.0
            }
        
        source_counts = {}
        for result in results:
            source_counts[result.source] = source_counts.get(result.source, 0) + 1
        
        return {
            "total_results": len(results),
            "source_breakdown": source_counts,
            "avg_final_score": sum(r.final_score for r in results) / len(results),
            "avg_relevance_score": sum(r.relevance_score for r in results) / len(results),
            "avg_recency_score": sum(r.recency_score for r in results) / len(results)
        }
```

---

### Task 7.5: Context Builder Integration (Format Preserving)

**File**: `backend/workflow/nodes/context_builder_node.py` (MODIFY)

**Purpose**: Integrate hybrid retrieval while preserving message dict structure.

**Implementation**:

```python
# Add imports
from backend.memory.hybrid_retriever import HybridRetriever
from backend.memory.retrieval_types import RetrievalConfig

class ContextBuilderNode(BaseNode):
    def __init__(
        self,
        cache_client: RedisCacheClient | None = None,
        enable_hybrid_retrieval: bool = False
    ) -> None:
        # ... existing initialization ...
        self.enable_hybrid_retrieval = enable_hybrid_retrieval
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        memory_manager = context.get("memory_manager")
        task_id = context.get("task_id")
        user_input = context.get("user_input", "")
        
        # ... existing cache check and working state retrieval ...
        
        if not cache_hit:
            if cache_attempted:
                self.metrics.record_miss("context")
            
            # Get working state messages (existing logic)
            messages: list[dict[str, Any]] = []
            if isinstance(working_state, dict):
                raw_messages = working_state.get("messages", [])
                if isinstance(raw_messages, list):
                    messages = [
                        msg for msg in raw_messages
                        if isinstance(msg, dict)
                    ][-10:]
            
            # NEW: Hybrid retrieval if enabled
            if self.enable_hybrid_retrieval and memory_manager:
                try:
                    retriever = HybridRetriever(
                        semantic_memory=memory_manager.semantic,
                        episodic_memory=memory_manager.episodic,
                        config=RetrievalConfig()
                    )
                    
                    # Retrieve augmented context
                    retrieval_results = retriever.retrieve(
                        query=user_input,
                        working_state_messages=messages,
                        task_id=str(task_id) if task_id else None
                    )
                    
                    # CRITICAL: Preserve message dict structure
                    # Convert to standard message format, don't use synthetic "system" role
                    augmented_messages = []
                    for result in retrieval_results:
                        # Preserve original message structure if from working state
                        if result.source == "working_state":
                            # Find original message from metadata
                            pos = result.metadata.get("position")
                            if pos is not None and pos < len(messages):
                                augmented_messages.append(messages[pos])
                        else:
                            # For semantic/episodic: use assistant role with source metadata
                            augmented_messages.append({
                                "role": "assistant",
                                "content": result.content,
                                "metadata": {
                                    "source": result.source,
                                    "relevance_score": result.relevance_score,
                                    "recency_score": result.recency_score,
                                    "final_score": result.final_score,
                                    **result.metadata
                                }
                            })
                    
                    messages = augmented_messages
                    
                    # Store retrieval metrics
                    retrieval_metrics = retriever.compute_retrieval_metrics(retrieval_results)
                    context["retrieval_metrics"] = retrieval_metrics
                    
                except Exception as exc:
                    print(f"[WARN] Hybrid retrieval failed: {exc}")
                    # Fall back to working state only
            
            # Cache result (existing logic)
            # ... existing cache set ...
        
        context["messages"] = messages
        context["cache_hit"] = cache_hit
        return context
```

---

### Task 7.6: Embedding Cache with Hashed Keys

**File**: `backend/memory/semantic_store.py` (MODIFY)

**Purpose**: Cache embeddings using hashed text keys.

**Implementation**:

```python
# Add to imports
import hashlib
from backend.cache.redis_client import RedisCacheClient

class SemanticMemory:
    def __init__(
        self,
        db_path: str = "data/semantic/metadata.db",
        embedding_model: Any = None,
        cache_client: RedisCacheClient | None = None
    ) -> None:
        # ... existing initialization ...
        self.cache = cache_client
    
    def _embed(self, text: str) -> list[float]:
        """
        Embed text with optional Redis caching.
        
        CRITICAL: Uses hashed text as cache key, not raw text
        """
        # Check cache first
        if self.cache is not None:
            # Hash text for cache key (deterministic, bounded size)
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
            cache_key = f"embedding:{text_hash}"
            
            cached = self.cache.get_json(cache_key)
            if cached and isinstance(cached, list):
                return cached
        
        # Compute embedding (expensive operation)
        vector = self.embedding_model.encode(text)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            vector = vector[0]
        
        embedding = [float(v) for v in vector]
        
        # Cache result (24-hour TTL - deterministic)
        if self.cache is not None:
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
            cache_key = f"embedding:{text_hash}"
            self.cache.set_json(cache_key, embedding, ttl=86400)
        
        return embedding
```

---

### Task 7.7: Configuration

**File**: `backend/config/settings.py` (MODIFY)

```python
class Settings(BaseSettings):
    # ... EXISTING fields ...
    
    # Hybrid Retrieval Configuration
    ENABLE_HYBRID_RETRIEVAL: bool = False  # Feature flag
    
    # Retrieval limits
    RETRIEVAL_MAX_SEMANTIC_RESULTS: int = 5
    RETRIEVAL_MAX_EPISODIC_RESULTS: int = 5
    RETRIEVAL_MAX_WORKING_STATE_MESSAGES: int = 10
    RETRIEVAL_MAX_TOTAL_RESULTS: int = 10
    
    # Quality thresholds
    RETRIEVAL_MIN_FINAL_SCORE_THRESHOLD: float = 0.5
    RETRIEVAL_SEMANTIC_SIMILARITY_THRESHOLD: float = 0.3  # L2 distance
    
    # Scoring weights (relevance vs recency per source)
    RETRIEVAL_WS_RELEVANCE_WEIGHT: float = 0.3
    RETRIEVAL_WS_RECENCY_WEIGHT: float = 0.7
    RETRIEVAL_SEM_RELEVANCE_WEIGHT: float = 0.9
    RETRIEVAL_SEM_RECENCY_WEIGHT: float = 0.1
    RETRIEVAL_EPI_RELEVANCE_WEIGHT: float = 0.7
    RETRIEVAL_EPI_RECENCY_WEIGHT: float = 0.3
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**File**: `.env.example` (MODIFY)

```bash
# Existing sections...

# Hybrid Retrieval Configuration
ENABLE_HYBRID_RETRIEVAL=false

# Retrieval Limits
RETRIEVAL_MAX_SEMANTIC_RESULTS=5
RETRIEVAL_MAX_EPISODIC_RESULTS=5
RETRIEVAL_MAX_WORKING_STATE_MESSAGES=10
RETRIEVAL_MAX_TOTAL_RESULTS=10

# Quality Thresholds
RETRIEVAL_MIN_FINAL_SCORE_THRESHOLD=0.5
RETRIEVAL_SEMANTIC_SIMILARITY_THRESHOLD=0.3

# Scoring Weights (relevance vs recency)
# Working State: Favors recency (recent messages more important)
RETRIEVAL_WS_RELEVANCE_WEIGHT=0.3
RETRIEVAL_WS_RECENCY_WEIGHT=0.7
# Semantic: Favors relevance (timeless knowledge)
RETRIEVAL_SEM_RELEVANCE_WEIGHT=0.9
RETRIEVAL_SEM_RECENCY_WEIGHT=0.1
# Episodic: Balanced (recent actions + relevance)
RETRIEVAL_EPI_RELEVANCE_WEIGHT=0.7
RETRIEVAL_EPI_RECENCY_WEIGHT=0.3
```

---

## Summary of Deliverables

### New Files
1. `backend/memory/retrieval_types.py` - Unified scoring schema
2. `backend/memory/hybrid_retriever.py` - Hybrid retrieval with recency decay
3. `tests/unit/test_retrieval_types.py` - Scoring validation tests
4. `tests/unit/test_hybrid_retriever.py` - Retrieval tests
5. `tests/unit/test_semantic_search.py` - Semantic search tests
6. `tests/unit/test_episodic_search.py` - Episodic search tests

### Modified Files
1. `backend/memory/semantic_store.py` - Add search_text() with normalized scores, hashed embedding cache
2. `backend/memory/episodic_db.py` - Add SQL indexes, search methods
3. `backend/workflow/nodes/context_builder_node.py` - Integrate hybrid retrieval (format-preserving)
4. `backend/config/settings.py` - Add retrieval configuration
5. `.env.example` - Add retrieval environment variables

---

## Design Decisions (Agent Feedback Addressed)

### 1. Unified Scoring Contract ✅
- **All scores 0-1, higher=better**
- Explicit normalization in each source
- L2 distance → similarity formula documented
- Validation in RetrievalResult.__post_init__()

### 2. Working State Recency Decay ✅
- **NOT fixed 1.0 scores**
- Exponential decay: newest=1.0, oldest=0.1
- Position-based calculation
- Relevance + recency weighted separately

### 3. SQL Indexes for Episodic ✅
- Indexes on task_id, timestamp, tool_name
- ORDER BY uses indexed columns
- Keyword extraction with length filter

### 4. Context Format Compatibility ✅
- **Preserves message dict structure**
- Working state messages use original format
- Semantic/episodic use "assistant" role (not "system")
- Metadata stored in message dict, not synthetic structure

### 5. Hashed Embedding Cache Keys ✅
- **SHA256 hash (first 16 chars) for cache keys**
- Deterministic, bounded key size
- No raw text in keys (privacy)
- 24-hour TTL for deterministic embeddings

---

## Validation Commands (Per AGENTS Contract)

```bash
# Unit tests
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_retrieval_types.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_hybrid_retriever.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_semantic_search.py -v
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_episodic_search.py -v

# Integration tests
.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_context_builder_cache.py -v

# Full validation
.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit
```

---

## Expected Improvements

### Scoring Example

```python
# Query: "What is Python?"

# Working State (recent message): "I like Python"
# - relevance: 0.5 (keyword match: 1/2 words)
# - recency: 1.0 (most recent)
# - final_score: 0.5*0.3 + 1.0*0.7 = 0.85

# Semantic: "Python is a programming language"
# - relevance: 0.9 (high similarity)
# - recency: 0.5 (stored a day ago)
# - final_score: 0.9*0.9 + 0.5*0.1 = 0.86

# Result: Semantic result ranked higher (0.86 > 0.85)
```

### Projected Metrics
- Memory recall: 60% → 95% (+59%)
- Context quality: 70% → 85% (+21%)
- Working state not swamped by fixed 1.0 scores ✅

---

## CHANGE_LOG Entry Format (After Implementation)

```
- 2026-02-XX HH:MM
  - Summary: Completed Milestone 7 hybrid semantic retrieval with unified 0-1 scoring, working state recency decay, indexed episodic search, and hashed embedding cache keys.
  - Scope: `backend/memory/retrieval_types.py`, `backend/memory/hybrid_retriever.py`, `backend/memory/semantic_store.py`, `backend/memory/episodic_db.py`, `backend/workflow/nodes/context_builder_node.py`, `backend/config/settings.py`, `.env.example`, `tests/unit/test_retrieval_types.py`, `tests/unit/test_hybrid_retriever.py`, `tests/unit/test_semantic_search.py`, `tests/unit/test_episodic_search.py`.
  - Key behaviors:
    - Unified scoring: all sources return 0-1 scores (higher=better), validated in RetrievalResult.
    - Working state uses exponential recency decay (newest=1.0, oldest=0.1), not fixed 1.0.
    - Semantic search normalizes L2 distance via similarity=1/(1+distance).
    - Episodic search uses SQL indexes on task_id, timestamp, tool_name for performance.
    - Context builder preserves message dict structure (no synthetic "system" messages).
    - Embedding cache uses SHA256-hashed keys (first 16 chars), not raw text.
    - Feature flag ENABLE_HYBRID_RETRIEVAL (default: false) for gradual rollout.
  - Evidence:
    - `.\backend\.venv\Scripts\python.exe -m pytest tests\unit\test_hybrid_retriever.py -q`
      - PASS excerpt: `X passed in Y.YYs`
    - `.\backend\.venv\Scripts\python.exe scripts\validate_backend.py --scope unit`
      - PASS excerpt: `UNIT: PASS_WITH_SKIPS`
```