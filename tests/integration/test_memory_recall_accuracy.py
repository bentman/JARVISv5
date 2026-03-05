from __future__ import annotations

"""
Memory Recall Accuracy Validation (Project.md §10.2 / Task 10.2)

Offline benchmark metrics and gates:
- Precision@k: relevant hits in top-k / k
- Recall@k: relevant hits in top-k / total relevant
- MRR: reciprocal rank of first relevant hit
- NDCG@10: graded ranking quality using qrels relevance labels (0..3)

Determinism rules:
- Fixed benchmark fixtures (versioned under tests/fixtures/retrieval_benchmark/v1)
- Fixed top-k set: [1, 3, 5, 10]
- Explicit tie handling via retrieval implementation stable ordering
- In-process deterministic embedding model for repeatable ranking behavior
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.memory.memory_manager import MemoryManager
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.retrieval_types import RetrievalConfig, RetrievalResult
from backend.workflow.nodes.context_builder_node import ContextBuilderNode


FIXTURE_DIR = Path("tests/fixtures/retrieval_benchmark/v1")
CORPUS_FILE = FIXTURE_DIR / "corpus.json"
QUERIES_FILE = FIXTURE_DIR / "queries.json"
QRELS_FILE = FIXTURE_DIR / "qrels.json"
DOC_ID_RE = re.compile(r"\bDOC_[A-Z]{1,2}_\d{4}\b")
TOPIC_TOKEN_RE = re.compile(r"\bKEY_TOPIC_\d{2}\b")


class _BenchmarkEmbeddingModel:
    """Deterministic topic-token embedding for offline benchmark reproducibility."""

    _topic_re = re.compile(r"KEY_TOPIC_(\d{2})")

    def encode(self, text: str) -> list[float]:
        vector = [0.0] * 32
        raw = str(text)
        match = self._topic_re.search(raw)
        if match:
            topic_idx = int(match.group(1)) % 20
            vector[topic_idx] = 1.0
        # Stable lexical fallback so non-token strings still map deterministically.
        for idx, ch in enumerate(raw):
            vector[20 + (idx % 12)] += (ord(ch) % 31) / 310.0
        return vector


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    query_text: str
    scenario: str
    task_id: str | None


def _build_memory_manager(root: Path) -> MemoryManager:
    return MemoryManager(
        episodic_db_path=str(root / "episodic" / "trace.db"),
        working_base_path=str(root / "working_state"),
        working_archive_path=str(root / "archives"),
        semantic_db_path=str(root / "semantic" / "metadata.db"),
        embedding_model=_BenchmarkEmbeddingModel(),
    )


def _load_benchmark() -> tuple[list[dict[str, Any]], list[QuerySpec], dict[str, dict[str, int]]]:
    corpus_payload = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    query_payload = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    qrels_payload = json.loads(QRELS_FILE.read_text(encoding="utf-8"))

    entries = list(corpus_payload.get("entries", []))
    queries = [
        QuerySpec(
            query_id=str(item["query_id"]),
            query_text=str(item["query_text"]),
            scenario=str(item["scenario"]),
            task_id=(str(item["task_id"]) if item.get("task_id") else None),
        )
        for item in query_payload.get("queries", [])
    ]

    qrels: dict[str, dict[str, int]] = {}
    for row in qrels_payload.get("qrels", []):
        qid = str(row["query_id"])
        did = str(row["doc_id"])
        rel = int(row["relevance"])
        qrels.setdefault(qid, {})[did] = rel

    return entries, queries, qrels


def _seed_memory(memory: MemoryManager, entries: list[dict[str, Any]], *, include_sources: set[str]) -> None:
    created_tasks: set[str] = set()
    token_task_map: dict[str, str] = {}
    for entry in entries:
        if str(entry.get("source", "")).strip() != "working_state":
            continue
        token = str(entry.get("token", "")).strip()
        task_id = str(entry.get("task_id", "")).strip()
        if token and task_id and token not in token_task_map:
            token_task_map[token] = task_id

    for entry in entries:
        source = str(entry.get("source", "")).strip()
        if source not in include_sources:
            continue

        doc_id = str(entry["doc_id"])
        text = str(entry["text"])
        topic = str(entry.get("topic", ""))
        token = str(entry.get("token", ""))

        if source == "semantic":
            metadata = dict(entry.get("metadata", {}))
            metadata.update({"doc_id": doc_id, "topic": topic, "token": token, "source": source})
            memory.store_knowledge(text, metadata)
            continue

        if source == "episodic_decision":
            episodic_task_id = str(entry.get("task_id") or token_task_map.get(token) or f"episodic-{topic}")
            content = json.dumps({"doc_id": doc_id, "topic": topic, "token": token, "text": text}, sort_keys=True)
            memory.log_decision(
                task_id=episodic_task_id,
                action_type="benchmark_decision",
                content=content,
                status="ok",
            )
            continue

        if source == "episodic_toolcall":
            episodic_task_id = str(entry.get("task_id") or token_task_map.get(token) or f"episodic-{topic}")
            decision_id = memory.log_decision(
                task_id=episodic_task_id,
                action_type="benchmark_tool_seed",
                content=json.dumps({"seed": doc_id, "token": token}, sort_keys=True),
                status="ok",
            )
            memory.log_tool_call(
                decision_id=decision_id,
                tool_name="benchmark_tool",
                params=json.dumps({"doc_id": doc_id, "token": token, "topic": topic}, sort_keys=True),
                result=json.dumps({"doc_id": doc_id, "text": text}, sort_keys=True),
            )
            continue

        if source == "working_state":
            task_id = str(entry.get("task_id") or f"ws-{topic}")
            if task_id not in created_tasks:
                memory.create_task(task_id, f"benchmark {topic}", ["PLAN", "EXECUTE", "VALIDATE", "COMMIT", "ARCHIVE"])
                created_tasks.add(task_id)
            memory.append_task_message(task_id, "assistant", f"[{doc_id}] {text}", max_messages=100)
            continue


def _extract_doc_id_from_result(result: RetrievalResult) -> str | None:
    metadata_doc_id = result.metadata.get("doc_id")
    if isinstance(metadata_doc_id, str) and metadata_doc_id.strip():
        return metadata_doc_id.strip()
    match = DOC_ID_RE.search(str(result.content))
    if match:
        return match.group(0)
    return None


def _extract_doc_ids_from_context_message(message: str) -> list[str]:
    ids: list[str] = []
    for line in message.splitlines():
        match = DOC_ID_RE.search(line)
        if match:
            ids.append(match.group(0))
    return ids


def _query_token(query_text: str) -> str:
    match = TOPIC_TOKEN_RE.search(str(query_text))
    if not match:
        raise AssertionError(f"query missing KEY_TOPIC token: {query_text}")
    return match.group(0)


def _subset_for_token(entries: list[dict[str, Any]], token: str, *, include_sources: set[str]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in entries
        if str(entry.get("source", "")) in include_sources and str(entry.get("token", "")) == token
    ]


def _precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top = retrieved[:k]
    if not top:
        return 0.0
    hits = sum(1 for doc_id in top if doc_id in relevant)
    return hits / float(k)


def _recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    hits = sum(1 for doc_id in top if doc_id in relevant)
    return hits / float(len(relevant))


def _mrr(retrieved: list[str], relevant: set[str]) -> float:
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / float(idx)
    return 0.0


def _ndcg_at_k(retrieved: list[str], graded_relevance: dict[str, int], k: int) -> float:
    import math

    gains = []
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        rel = int(graded_relevance.get(doc_id, 0))
        gains.append((2**rel - 1) / math.log2(rank + 1))
    dcg = sum(gains)

    ideal_rels = sorted((int(v) for v in graded_relevance.values()), reverse=True)[:k]
    ideal = [((2**rel) - 1) / math.log2(rank + 1) for rank, rel in enumerate(ideal_rels, start=1)]
    idcg = sum(ideal)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def test_semantic_recall_precision_recall_mrr_at_k(tmp_path: Path) -> None:
    entries, queries, qrels = _load_benchmark()
    semantic_queries = [q for q in queries if q.scenario == "semantic"]
    assert len(semantic_queries) >= 8

    memory = _build_memory_manager(tmp_path / "semantic")
    _seed_memory(memory, entries, include_sources={"semantic"})

    p_at_5: list[float] = []
    r_at_10: list[float] = []
    mrr_scores: list[float] = []

    for query in semantic_queries:
        graded = qrels[query.query_id]
        relevant = {doc_id for doc_id, rel in graded.items() if rel >= 1}

        rows = memory.semantic.search_text(query.query_text, top_k=10)
        ranked = [str(row.get("metadata", {}).get("doc_id", "")) for row in rows if row.get("metadata")]

        p_at_5.append(_precision_at_k(ranked, relevant, 5))
        r_at_10.append(_recall_at_k(ranked, relevant, 10))
        mrr_scores.append(_mrr(ranked, relevant))

    precision_5 = sum(p_at_5) / len(p_at_5)
    recall_10 = sum(r_at_10) / len(r_at_10)
    mean_rr = sum(mrr_scores) / len(mrr_scores)

    assert precision_5 >= 0.95, f"Precision@5 below gate: {precision_5:.4f}"
    assert recall_10 >= 0.95, f"Recall@10 below gate: {recall_10:.4f}"
    assert mean_rr >= 0.95, f"MRR unexpectedly low: {mean_rr:.4f}"


def test_episodic_search_relevance_coverage(tmp_path: Path) -> None:
    entries, queries, qrels = _load_benchmark()
    episodic_queries = [q for q in queries if q.scenario == "episodic"]
    assert len(episodic_queries) >= 4

    memory = _build_memory_manager(tmp_path / "episodic")
    _seed_memory(memory, entries, include_sources={"episodic_decision", "episodic_toolcall"})

    relevance_scores: list[float] = []
    coverage_scores: list[float] = []

    for query in episodic_queries:
        graded = qrels[query.query_id]
        relevant = {doc_id for doc_id, rel in graded.items() if rel >= 1}

        decision_rows = memory.episodic.search_decisions(query.query_text, limit=10)
        tool_rows = memory.episodic.search_tool_calls(query.query_text, limit=10)

        ranked: list[str] = []
        for row in decision_rows:
            match = DOC_ID_RE.search(str(row.get("content", "")))
            if match:
                ranked.append(match.group(0))
        for row in tool_rows:
            combined = f"{row.get('params','')} {row.get('result','')}"
            match = DOC_ID_RE.search(combined)
            if match:
                ranked.append(match.group(0))

        deduped: list[str] = []
        seen: set[str] = set()
        for doc_id in ranked:
            if doc_id not in seen:
                deduped.append(doc_id)
                seen.add(doc_id)

        top = deduped[:5]
        if not top:
            relevance_scores.append(0.0)
            coverage_scores.append(0.0)
            continue

        hits = sum(1 for doc_id in top if doc_id in relevant)
        relevance_scores.append(hits / float(len(top)))
        coverage_scores.append(hits / float(len(relevant)))

    relevance = sum(relevance_scores) / len(relevance_scores)
    coverage = sum(coverage_scores) / len(coverage_scores)

    assert relevance >= 0.95, f"Episodic relevance below gate: {relevance:.4f}"
    assert coverage >= 0.95, f"Episodic coverage below gate: {coverage:.4f}"


def test_hybrid_retrieval_ranking_ndcg_at_10(tmp_path: Path) -> None:
    entries, queries, qrels = _load_benchmark()
    hybrid_queries = [q for q in queries if q.scenario == "hybrid"]
    assert len(hybrid_queries) >= 4

    ndcgs: list[float] = []
    for idx, query in enumerate(hybrid_queries):
        token = _query_token(query.query_text)
        memory = _build_memory_manager(tmp_path / "hybrid" / f"q_{idx}")
        _seed_memory(
            memory,
            _subset_for_token(
                entries,
                token,
                include_sources={"semantic", "episodic_decision", "episodic_toolcall", "working_state"},
            ),
            include_sources={"semantic", "episodic_decision", "episodic_toolcall", "working_state"},
        )
        retriever = HybridRetriever(
            semantic_store=memory.semantic,
            episodic_memory=memory.episodic,
            working_state_provider=lambda task_id: memory.get_task_state(task_id),
        )
        config = RetrievalConfig(max_results=10)
        results = retriever.retrieve(
            query.query_text,
            task_id=query.task_id,
            turn=0,
            config=config,
            limit=10,
        )
        ranked = [doc_id for doc_id in (_extract_doc_id_from_result(item) for item in results) if doc_id]
        ndcgs.append(_ndcg_at_k(ranked, qrels[query.query_id], 10))

    avg_ndcg = sum(ndcgs) / len(ndcgs)
    assert avg_ndcg >= 0.90, f"Hybrid NDCG@10 below gate: {avg_ndcg:.4f}"


def test_context_builder_relevance_filtering_top5(tmp_path: Path) -> None:
    entries, queries, qrels = _load_benchmark()
    context_queries = [q for q in queries if q.scenario == "context_builder"]
    assert len(context_queries) >= 4

    relevance_ratios: list[float] = []
    for idx, query in enumerate(context_queries):
        token = _query_token(query.query_text)
        memory = _build_memory_manager(tmp_path / "context" / f"q_{idx}")
        _seed_memory(
            memory,
            _subset_for_token(
                entries,
                token,
                include_sources={"semantic", "episodic_decision", "episodic_toolcall", "working_state"},
            ),
            include_sources={"semantic", "episodic_decision", "episodic_toolcall", "working_state"},
        )
        retriever = HybridRetriever(
            semantic_store=memory.semantic,
            episodic_memory=memory.episodic,
            working_state_provider=lambda task_id: memory.get_task_state(task_id),
        )
        context_builder = ContextBuilderNode(
            retriever=retriever,
            retrieval_config=RetrievalConfig(max_results=5),
            retrieval_message_max_chars=500,
        )
        context = {
            "memory_manager": memory,
            "task_id": query.task_id,
            "turn": 0,
            "user_input": query.query_text,
        }
        out = context_builder.execute(context)
        messages = out.get("messages", [])
        retrieved_message = ""
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if str(msg.get("role")) == "system" and str(msg.get("content", "")).startswith("Retrieved Context:"):
                retrieved_message = str(msg.get("content", ""))
                break

        doc_ids = _extract_doc_ids_from_context_message(retrieved_message)[:5]
        graded = qrels[query.query_id]
        relevant = {doc_id for doc_id, rel in graded.items() if rel >= 1}
        if len(doc_ids) < 5:
            relevance_ratios.append(0.0)
            continue
        hits = sum(1 for doc_id in doc_ids if doc_id in relevant)
        relevance_ratios.append(hits / 5.0)

    avg_ratio = sum(relevance_ratios) / len(relevance_ratios)
    assert avg_ratio >= 0.95, f"Context builder top-5 relevance below gate: {avg_ratio:.4f}"
