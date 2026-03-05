from __future__ import annotations

"""
Drift Rate Measurement (Project.md §10.2 / Task 10.4)

Deterministic protocol:
- Warm-up policy: 3 non-measured runs before measured loops.
- Offline-only inputs: retrieval benchmark fixtures under
  tests/fixtures/retrieval_benchmark/v1.
- Canonicalization excludes volatile fields when comparing orchestration artifacts:
  task_id, id, decision_id, timestamp, elapsed_ns, start_offset_ns,
  modified_epoch, path.

Metrics used in this module:
- Exact match rate (string equality)
- Cosine similarity (deterministic embedding vectors)
- Levenshtein edit distance (pure-python, deterministic)

BLEU note:
- No BLEU dependency is declared in backend/requirements.txt, so BLEU is
  intentionally omitted here.

Fixed-seed variance prerequisite note:
- test_model_output_variance_fixed_seed requires explicit seed control wired into
  generation settings or completion call parameters. If seed control is not
  discoverable in repository code/config, the test is skipped with a clear message.
"""

import inspect
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from backend.config.settings import Settings
from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService
from backend.models.local_inference import LocalInferenceClient
from backend.models.model_registry import ModelRegistry
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.retrieval_types import RetrievalConfig
from backend.workflow.nodes.llm_worker_node import LLMWorkerNode


VOLATILE_FIELDS: set[str] = {
    "task_id",
    "id",
    "decision_id",
    "timestamp",
    "elapsed_ns",
    "start_offset_ns",
    "modified_epoch",
    "path",
}


FIXTURE_DIR = Path("tests/fixtures/retrieval_benchmark/v1")
CORPUS_FILE = FIXTURE_DIR / "corpus.json"
QUERIES_FILE = FIXTURE_DIR / "queries.json"


class _DeterministicEmbeddingModel:
    def encode(self, text: str) -> list[float]:
        vec = [0.0] * 32
        raw = str(text)
        for idx, ch in enumerate(raw):
            vec[idx % 32] += (ord(ch) % 97) / 97.0
        return vec


def _build_memory_manager(root: Path) -> MemoryManager:
    return MemoryManager(
        episodic_db_path=str(root / "episodic" / "trace.db"),
        working_base_path=str(root / "working_state"),
        working_archive_path=str(root / "archives"),
        semantic_db_path=str(root / "semantic" / "metadata.db"),
        embedding_model=_DeterministicEmbeddingModel(),
    )


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key in sorted(value.keys()):
            if key in VOLATILE_FIELDS:
                continue
            out[key] = _strip_volatile(value[key])
        return out
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _canonical_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = sorted(str(item) for item in graph.get("nodes", []))
    edges_raw = graph.get("edges", [])
    edges: list[dict[str, str]] = []
    if isinstance(edges_raw, list):
        for edge in edges_raw:
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("from") or edge.get("from_node") or "")
            dst = str(edge.get("to") or edge.get("to_node") or "")
            edges.append({"from": src, "to": dst})
    edges.sort(key=lambda item: (item["from"], item["to"]))
    return {"nodes": nodes, "edges": edges, "entry": str(graph.get("entry", ""))}


def _load_dag_events(episodic_db_path: Path, task_id: str) -> list[dict[str, Any]]:
    if not episodic_db_path.exists():
        return []
    with sqlite3.connect(str(episodic_db_path)) as conn:
        rows = conn.execute(
            """
            SELECT content
            FROM decisions
            WHERE task_id = ? AND action_type = 'dag_node_event'
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for (content,) in rows:
        payload = json.loads(str(content))
        out.append(_strip_volatile(payload))
    return out


def _orchestration_signature(run_result: dict[str, Any], memory_root: Path) -> dict[str, Any]:
    context = run_result.get("context", {}) if isinstance(run_result.get("context"), dict) else {}
    task_id = str(run_result.get("task_id", ""))
    graph = context.get("workflow_graph", {}) if isinstance(context.get("workflow_graph"), dict) else {}
    order = context.get("workflow_execution_order", []) if isinstance(context.get("workflow_execution_order"), list) else []
    dag_events = _load_dag_events(memory_root / "episodic" / "trace.db", task_id)
    return {
        "final_state": str(run_result.get("final_state", "")),
        "archived": bool(run_result.get("archived", False)),
        "intent": str(context.get("intent", "")),
        "is_valid": bool(context.get("is_valid", False)),
        "workflow_graph": _canonical_graph(graph),
        "workflow_execution_order": [str(item) for item in order],
        "dag_events": dag_events,
    }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _levenshtein_distance(a: str, b: str) -> int:
    left = str(a)
    right = str(b)
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    prev = list(range(len(right) + 1))
    for i, ch_left in enumerate(left, start=1):
        curr = [i]
        for j, ch_right in enumerate(right, start=1):
            cost = 0 if ch_left == ch_right else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _normalized_edit_similarity(a: str, b: str) -> float:
    max_len = max(len(a), len(b), 1)
    return 1.0 - (_levenshtein_distance(a, b) / float(max_len))


def _load_retrieval_fixture_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    queries = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    entries = list(corpus.get("entries", []))
    query_rows = list(queries.get("queries", []))
    return entries, query_rows


def _seed_semantic_entries(memory: MemoryManager, entries: list[dict[str, Any]], top_n: int = 40) -> None:
    count = 0
    for row in entries:
        if str(row.get("source", "")).strip() != "semantic":
            continue
        text = str(row.get("text", ""))
        metadata = dict(row.get("metadata", {}))
        metadata.update(
            {
                "doc_id": str(row.get("doc_id", "")),
                "topic": str(row.get("topic", "")),
            }
        )
        memory.store_knowledge(text, metadata)
        count += 1
        if count >= top_n:
            break


def _extract_doc_ids(results: list[dict[str, Any]]) -> list[str]:
    doc_ids: list[str] = []
    for row in results:
        metadata = row.get("metadata", {}) if isinstance(row.get("metadata"), dict) else {}
        doc_id = str(metadata.get("doc_id", "")).strip()
        if doc_id:
            doc_ids.append(doc_id)
    return doc_ids


def _generation_seed_control() -> tuple[bool, str]:
    settings_fields = {name.upper() for name in Settings.model_fields.keys()}
    seed_field_candidates = {"SEED", "MODEL_SEED", "LLM_SEED", "INFERENCE_SEED", "GENERATION_SEED"}
    for name in seed_field_candidates:
        if name in settings_fields:
            return True, f"Settings field found: {name}"

    worker_src = inspect.getsource(LLMWorkerNode.execute)
    if "seed=" in worker_src:
        return True, "LLMWorkerNode.execute passes seed=... to create_completion"

    local_src = inspect.getsource(LocalInferenceClient.generate)
    if "seed=" in local_src:
        return True, "LocalInferenceClient.generate passes seed=... to create_completion"

    return False, "seed control not wired; required for fixed-seed variance test"


def calculate_drift_rate(
    *,
    orchestration_consistency: float,
    retrieval_stability: float,
    generation_stability: float,
) -> dict[str, float | bool]:
    orchestration_drift = 1.0 - float(orchestration_consistency)
    retrieval_drift = 1.0 - float(retrieval_stability)
    generation_drift = 1.0 - float(generation_stability)
    overall = (orchestration_drift + retrieval_drift + generation_drift) / 3.0
    return {
        "orchestration_drift_rate": orchestration_drift,
        "retrieval_drift_rate": retrieval_drift,
        "generation_drift_rate": generation_drift,
        "overall_drift_rate": overall,
        "drift_percentage": overall * 100.0,
        "target_met": overall < 0.05,
    }


@pytest.fixture
def deterministic_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HWType:
        value = "CPU_ONLY"

    monkeypatch.setattr(HardwareService, "get_hardware_profile", lambda self: "TEST")
    monkeypatch.setattr(HardwareService, "detect_hardware_type", lambda self: _HWType())
    monkeypatch.setattr(ModelRegistry, "select_model", lambda self, profile, hardware, role: None)


@pytest.fixture
def fixed_seed_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HWType:
        value = "CPU_ONLY"

    class _StubLlama:
        _counter = 0

        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs) -> dict[str, Any]:
            seed = kwargs.get("seed")
            if seed is None:
                type(self)._counter += 1
                text = f"seed-missing-{type(self)._counter}"
            else:
                text = f"seeded-output-{int(seed)}"
            return {"choices": [{"text": text}]}

    monkeypatch.setattr(HardwareService, "get_hardware_profile", lambda self: "TEST")
    monkeypatch.setattr(HardwareService, "detect_hardware_type", lambda self: _HWType())
    monkeypatch.setattr(ModelRegistry, "select_model", lambda self, profile, hardware, role: {"path": "models/test-model.gguf"})
    monkeypatch.setattr(ModelRegistry, "ensure_model_present", lambda self, model: str(model.get("path", "models/test-model.gguf")))
    monkeypatch.setitem(__import__("sys").modules, "llama_cpp", __import__("types").SimpleNamespace(Llama=_StubLlama))
    monkeypatch.setenv("GENERATION_SEED", "42")


def test_output_stability_repeated_inputs(tmp_path: Path, deterministic_runtime: None) -> None:
    memory = _build_memory_manager(tmp_path / "output_stability")
    controller = ControllerService(memory_manager=memory)
    user_input = "Summarize deterministic orchestration behavior in one line."

    for _ in range(3):
        controller.run(user_input=user_input)

    outputs: list[str] = []
    embedder = _DeterministicEmbeddingModel()
    for _ in range(10):
        run = controller.run(user_input=user_input)
        context = run.get("context", {}) if isinstance(run.get("context"), dict) else {}
        outputs.append(str(context.get("llm_output", "")))

    baseline = outputs[0] if outputs else ""
    exact_match_rate = sum(1 for item in outputs if item == baseline) / float(len(outputs) or 1)
    edit_similarities = [_normalized_edit_similarity(baseline, item) for item in outputs]
    cosine_scores = [
        _cosine_similarity(embedder.encode(baseline), embedder.encode(item))
        for item in outputs
    ]

    generation_stability = (exact_match_rate + (sum(cosine_scores) / len(cosine_scores))) / 2.0
    drift = calculate_drift_rate(
        orchestration_consistency=1.0,
        retrieval_stability=1.0,
        generation_stability=generation_stability,
    )

    assert exact_match_rate >= 0.95, f"Exact match rate {exact_match_rate:.2%} < 95%"
    assert (sum(edit_similarities) / len(edit_similarities)) >= 0.95
    assert drift["generation_drift_rate"] <= 0.05


def test_semantic_embedding_stability(tmp_path: Path) -> None:
    entries, query_rows = _load_retrieval_fixture_data()
    memory = _build_memory_manager(tmp_path / "embedding_stability")
    _seed_semantic_entries(memory, entries, top_n=40)

    semantic_query = ""
    for row in query_rows:
        if str(row.get("scenario", "")).strip() == "semantic":
            semantic_query = str(row.get("query_text", ""))
            break
    if not semantic_query:
        semantic_query = "KEY_TOPIC_00 deterministic retrieval"

    first_results = memory.semantic.search_text(semantic_query, top_k=10)
    second_results = memory.semantic.search_text(semantic_query, top_k=10)

    first_doc_ids = _extract_doc_ids(first_results)
    second_doc_ids = _extract_doc_ids(second_results)
    rank_stability = 1.0 if first_doc_ids == second_doc_ids else 0.0

    embedder = _DeterministicEmbeddingModel()
    sims: list[float] = []
    for row_a, row_b in zip(first_results, second_results):
        text_a = str(row_a.get("text", ""))
        text_b = str(row_b.get("text", ""))
        sims.append(_cosine_similarity(embedder.encode(text_a), embedder.encode(text_b)))
    mean_cosine = sum(sims) / float(len(sims) or 1)

    drift = calculate_drift_rate(
        orchestration_consistency=1.0,
        retrieval_stability=(rank_stability + mean_cosine) / 2.0,
        generation_stability=1.0,
    )

    assert mean_cosine >= 0.99, f"Mean cosine similarity {mean_cosine:.4f} < 0.99"
    assert rank_stability >= 0.95, "Retrieval rank stability below 95%"
    assert drift["retrieval_drift_rate"] <= 0.05


def test_decision_consistency_across_runs(tmp_path: Path, deterministic_runtime: None) -> None:
    prompts = [
        "What is 2+2?",
        "Write code for sorting a list",
        "Explain caching briefly",
        "Show code to reverse a string",
        "What is deterministic testing?",
        "Need code for binary search",
        "How does retrieval ranking work?",
        "Share code for a palindrome check",
        "Define validation gate",
        "Provide code for fibonacci",
    ]

    matches = 0
    for idx, prompt in enumerate(prompts):
        run_a_root = tmp_path / "decision_consistency" / f"a_{idx}"
        run_b_root = tmp_path / "decision_consistency" / f"b_{idx}"
        controller_a = ControllerService(memory_manager=_build_memory_manager(run_a_root))
        controller_b = ControllerService(memory_manager=_build_memory_manager(run_b_root))

        run_a = controller_a.run(user_input=prompt)
        run_b = controller_b.run(user_input=prompt)

        sig_a = _orchestration_signature(run_a, run_a_root)
        sig_b = _orchestration_signature(run_b, run_b_root)
        if sig_a == sig_b:
            matches += 1

    consistency = matches / float(len(prompts))
    drift = calculate_drift_rate(
        orchestration_consistency=consistency,
        retrieval_stability=1.0,
        generation_stability=1.0,
    )

    assert consistency >= 0.95, f"Decision consistency {consistency:.2%} < 95%"
    assert drift["orchestration_drift_rate"] <= 0.05


def test_model_output_variance_fixed_seed(tmp_path: Path, fixed_seed_runtime: None) -> None:
    """
    Fixed-seed output variance test.

    Prerequisite:
    - Seed control must be wired in settings/env or inference completion params.
    - If seed control is absent, this test is intentionally skipped (per Task 10.4
      adjustment requirement) rather than using fallback-mode stand-ins.
    """
    available, reason = _generation_seed_control()
    if not available:
        pytest.skip(reason)

    memory = _build_memory_manager(tmp_path / "fixed_seed_variance")
    controller = ControllerService(
        memory_manager=memory,
        generation_seed=Settings().GENERATION_SEED,
    )
    user_input = "Provide a concise summary of deterministic workflows."

    for _ in range(3):
        controller.run(user_input=user_input)

    outputs: list[str] = []
    embedder = _DeterministicEmbeddingModel()
    for _ in range(100):
        run = controller.run(user_input=user_input)
        context = run.get("context", {}) if isinstance(run.get("context"), dict) else {}
        outputs.append(str(context.get("llm_output", "")))

    assert all(item == "seeded-output-42" for item in outputs), "fixed-seed protocol not applied"

    baseline = outputs[0] if outputs else ""
    cosine_scores = [
        _cosine_similarity(embedder.encode(baseline), embedder.encode(item))
        for item in outputs
    ]
    edit_scores = [_normalized_edit_similarity(baseline, item) for item in outputs]

    generation_stability = ((sum(cosine_scores) / len(cosine_scores)) + (sum(edit_scores) / len(edit_scores))) / 2.0
    variance = 1.0 - generation_stability
    drift = calculate_drift_rate(
        orchestration_consistency=1.0,
        retrieval_stability=1.0,
        generation_stability=generation_stability,
    )

    assert variance <= 0.05, f"Model output variance {variance:.2%} > 5%"
    assert drift["generation_drift_rate"] <= 0.05
