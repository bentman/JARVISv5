from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models.hardware_profiler import HardwareService
from backend.models.model_registry import ModelRegistry
from backend.retrieval.hybrid_retriever import HybridRetriever
from backend.retrieval.retrieval_types import RetrievalConfig
from backend.workflow.nodes.context_builder_node import ContextBuilderNode


# Explicit volatile-field exclusions for Track A deterministic comparison.
VOLATILE_FIELDS: set[str] = {
    "task_id",            # can be generated per run unless explicitly supplied
    "timestamp",          # wall-clock time
    "id",                 # DB surrogate ids
    "decision_id",        # DB linkage ids
    "elapsed_ns",         # runtime timing noise
    "start_offset_ns",    # runtime timing noise
    "modified_epoch",     # filesystem clock value
    "path",               # absolute temp paths vary by run
}


class _DeterministicEmbeddingModel:
    def encode(self, text: str) -> list[float]:
        # Stable, lightweight embedding stub for deterministic in-process testing.
        values = [0.0] * 8
        raw = str(text)
        for idx, ch in enumerate(raw):
            values[idx % 8] += (ord(ch) % 97) / 97.0
        return values


@dataclass
class _RunArtifacts:
    task_id: str
    workflow_graph: dict[str, Any]
    dag_events: list[dict[str, Any]]
    task_state: dict[str, Any]
    decisions: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    retrieval_set: set[tuple[str, str]]
    semantic_rows: list[dict[str, Any]]


def _build_memory_manager(root: Path) -> MemoryManager:
    return MemoryManager(
        episodic_db_path=str(root / "episodic" / "trace.db"),
        working_base_path=str(root / "working_state"),
        working_archive_path=str(root / "archives"),
        semantic_db_path=str(root / "semantic" / "metadata.db"),
        embedding_model=_DeterministicEmbeddingModel(),
    )


def _decisions_high_water_mark(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM decisions").fetchone()
    return int(row[0]) if row else 0


def _tool_calls_high_water_mark(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tool_calls").fetchone()
    return int(row[0]) if row else 0


def _normalize_json_text(raw: str) -> Any:
    text = str(raw)
    try:
        parsed = json.loads(text)
    except Exception:
        return text
    return _strip_volatile(parsed)


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


def _canonicalize_workflow_graph(workflow_graph: dict[str, Any]) -> dict[str, Any]:
    nodes_raw = workflow_graph.get("nodes", [])
    edges_raw = workflow_graph.get("edges", [])
    entry_raw = workflow_graph.get("entry", "")

    nodes = sorted(str(node) for node in nodes_raw) if isinstance(nodes_raw, list) else []
    edges: list[dict[str, str]] = []
    if isinstance(edges_raw, list):
        for edge in edges_raw:
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("from") or edge.get("from_node") or "")
            dst = str(edge.get("to") or edge.get("to_node") or "")
            edges.append({"from": src, "to": dst})
    edges = sorted(edges, key=lambda item: (item["from"], item["to"]))

    return {
        "nodes": nodes,
        "edges": edges,
        "entry": str(entry_raw),
    }


def _canonicalize_dag_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    error_raw = payload.get("error")
    error_norm = str(error_raw).strip() if error_raw is not None else ""
    return {
        "event_type": str(payload.get("event_type", "")),
        "node_id": str(payload.get("node_id", "")),
        "node_type": str(payload.get("node_type", "")),
        "controller_state": str(payload.get("controller_state", "")),
        "success": bool(payload.get("success", False)),
        "error_norm": error_norm,
    }


def _fetch_canonical_dag_events(db_path: Path, task_id: str, min_decision_id: int) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT content
            FROM decisions
            WHERE id > ?
              AND task_id = ?
              AND action_type = 'dag_node_event'
            ORDER BY id ASC
            """,
            (int(min_decision_id), str(task_id)),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for (content,) in rows:
        payload = json.loads(content)
        out.append(_canonicalize_dag_event_payload(payload))
    return out


def _fetch_canonical_decisions(db_path: Path, task_id: str, min_decision_id: int) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT action_type, content, status
            FROM decisions
            WHERE id > ?
              AND task_id = ?
            ORDER BY id ASC
            """,
            (int(min_decision_id), str(task_id)),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for action_type, content, status in rows:
        if str(action_type) == "dag_node_event":
            parsed = json.loads(str(content))
            normalized_content: Any = _canonicalize_dag_event_payload(parsed)
        else:
            normalized_content = _normalize_json_text(str(content))
        out.append(
            {
                "action_type": str(action_type),
                "status": str(status),
                "content": normalized_content,
            }
        )
    return out


def _fetch_canonical_tool_calls(db_path: Path, task_id: str, min_tool_call_id: int) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT tc.tool_name, tc.params, tc.result
            FROM tool_calls tc
            INNER JOIN decisions d ON d.id = tc.decision_id
            WHERE tc.id > ?
              AND d.task_id = ?
            ORDER BY tc.id ASC
            """,
            (int(min_tool_call_id), str(task_id)),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for tool_name, params, result in rows:
        out.append(
            {
                "tool_name": str(tool_name),
                "params": _normalize_json_text(str(params)),
                "result": _normalize_json_text(str(result)),
            }
        )
    return out


def _load_archived_task_state(root: Path, task_id: str) -> dict[str, Any]:
    archive_path = root / "archives" / f"{task_id}.json"
    with archive_path.open("r", encoding="utf-8") as handle:
        task_state = json.load(handle)
    if not isinstance(task_state, dict):
        raise AssertionError("archived task state must be an object")
    return task_state


def _canonicalize_task_state(task_state: dict[str, Any]) -> dict[str, Any]:
    normalized = _strip_volatile(task_state)
    if isinstance(normalized, dict) and isinstance(normalized.get("workflow_graph"), dict):
        normalized["workflow_graph"] = _canonicalize_workflow_graph(normalized["workflow_graph"])
    return normalized


def _fetch_semantic_rows(memory_manager: MemoryManager) -> list[dict[str, Any]]:
    # Stable projection by querying deterministic corpus and sorting by content.
    rows = memory_manager.semantic.search_text("", top_k=1000)
    projection = [
        {
            "text": str(item.get("text", "")),
            "metadata": _strip_volatile(item.get("metadata", {})),
        }
        for item in rows
        if isinstance(item, dict)
    ]
    projection.sort(key=lambda item: (item["text"], json.dumps(item["metadata"], sort_keys=True)))
    return projection


def _capture_artifacts(
    memory_root: Path,
    controller: ControllerService,
    user_input: str,
    task_id: str | None = None,
    tool_call: dict[str, Any] | None = None,
) -> _RunArtifacts:
    db_path = memory_root / "episodic" / "trace.db"
    high_decision = _decisions_high_water_mark(db_path)
    high_tool_call = _tool_calls_high_water_mark(db_path)

    result = controller.run(user_input=user_input, task_id=task_id, tool_call=tool_call)
    if not bool(result.get("archived", False)):
        raise AssertionError(f"run did not archive: {result}")
    resolved_task_id = str(result.get("task_id", "")).strip()
    if not resolved_task_id:
        raise AssertionError("missing task_id in controller result")

    task_state = _load_archived_task_state(memory_root, resolved_task_id)
    workflow_graph = _canonicalize_workflow_graph(task_state.get("workflow_graph", {}))
    dag_events = _fetch_canonical_dag_events(db_path, resolved_task_id, high_decision)
    decisions = _fetch_canonical_decisions(db_path, resolved_task_id, high_decision)
    tool_calls = _fetch_canonical_tool_calls(db_path, resolved_task_id, high_tool_call)

    context = result.get("context", {}) if isinstance(result.get("context"), dict) else {}
    retrieval_items = context.get("retrieval_items", [])
    retrieval_set: set[tuple[str, str]] = set()
    if isinstance(retrieval_items, list):
        for item in retrieval_items:
            if not isinstance(item, dict):
                continue
            retrieval_set.add((str(item.get("source", "")), str(item.get("content", ""))))

    return _RunArtifacts(
        task_id=resolved_task_id,
        workflow_graph=workflow_graph,
        dag_events=dag_events,
        task_state=_canonicalize_task_state(task_state),
        decisions=decisions,
        tool_calls=tool_calls,
        retrieval_set=retrieval_set,
        semantic_rows=_fetch_semantic_rows(controller.memory),
    )


@pytest.fixture
def deterministic_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HWType:
        value = "CPU_ONLY"

    monkeypatch.setattr(HardwareService, "get_hardware_profile", lambda self: "TEST")
    monkeypatch.setattr(HardwareService, "detect_hardware_type", lambda self: _HWType())
    monkeypatch.setattr(ModelRegistry, "select_model", lambda self, profile, hardware, role: None)


@pytest.fixture
def retrieval_context_builder_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.controller import controller_service as controller_module

    class _RetrievalContextBuilderNode(ContextBuilderNode):
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            output = super().execute(context)
            memory_manager = output.get("memory_manager")
            if memory_manager is None:
                return output

            retriever = HybridRetriever(
                semantic_store=memory_manager.semantic,
                episodic_memory=memory_manager.episodic,
                working_state_provider=lambda tid: memory_manager.get_task_state(tid),
            )
            query = str(output.get("user_input", "")).strip()
            if not query:
                output["retrieval_items"] = []
                return output

            results = retriever.retrieve(
                query,
                task_id=str(output.get("task_id", "")) or None,
                turn=0,
                config=RetrievalConfig(),
                limit=10,
            )
            output["retrieval_items"] = [
                {
                    "source": item.source.value,
                    "content": item.content,
                }
                for item in results
            ]
            return output

    monkeypatch.setattr(controller_module, "ContextBuilderNode", _RetrievalContextBuilderNode)


def test_reproducibility_single_task_replay(tmp_path: Path, deterministic_runtime: None) -> None:
    run1_root = tmp_path / "single_run_1"
    run2_root = tmp_path / "single_run_2"

    run1_controller = ControllerService(memory_manager=_build_memory_manager(run1_root))
    run2_controller = ControllerService(memory_manager=_build_memory_manager(run2_root))

    run1 = _capture_artifacts(run1_root, run1_controller, user_input="Replay single deterministic")
    run2 = _capture_artifacts(run2_root, run2_controller, user_input="Replay single deterministic")

    assert run1.workflow_graph == run2.workflow_graph
    assert run1.dag_events == run2.dag_events
    assert run1.task_state == run2.task_state
    assert run1.decisions == run2.decisions
    assert run1.tool_calls == run2.tool_calls


def test_reproducibility_multi_turn_conversation(tmp_path: Path, deterministic_runtime: None) -> None:
    turns = ["Hello", "Please summarize prior context", "Final answer"]
    run1_root = tmp_path / "multi_run_1"
    run2_root = tmp_path / "multi_run_2"

    run1_controller = ControllerService(memory_manager=_build_memory_manager(run1_root))
    run2_controller = ControllerService(memory_manager=_build_memory_manager(run2_root))

    run1_results: list[_RunArtifacts] = []
    run2_results: list[_RunArtifacts] = []

    task_id_1: str | None = None
    task_id_2: str | None = None
    for turn in turns:
        res1 = _capture_artifacts(run1_root, run1_controller, user_input=turn, task_id=task_id_1)
        task_id_1 = res1.task_id
        run1_results.append(res1)

        res2 = _capture_artifacts(run2_root, run2_controller, user_input=turn, task_id=task_id_2)
        task_id_2 = res2.task_id
        run2_results.append(res2)

    assert len(run1_results) == len(run2_results)
    for idx in range(len(turns)):
        a = run1_results[idx]
        b = run2_results[idx]
        assert a.workflow_graph == b.workflow_graph
        assert a.dag_events == b.dag_events
        assert a.task_state == b.task_state
        assert a.decisions == b.decisions
        assert a.tool_calls == b.tool_calls


def test_reproducibility_tool_execution(tmp_path: Path, deterministic_runtime: None) -> None:
    run1_root = tmp_path / "tool_run_1"
    run2_root = tmp_path / "tool_run_2"
    sandbox_root_1 = tmp_path / "sandbox_1"
    sandbox_root_2 = tmp_path / "sandbox_2"
    sandbox_root_1.mkdir(parents=True, exist_ok=True)
    sandbox_root_2.mkdir(parents=True, exist_ok=True)

    rel_path = "notes.txt"
    (sandbox_root_1 / rel_path).write_text("deterministic tool content", encoding="utf-8")
    (sandbox_root_2 / rel_path).write_text("deterministic tool content", encoding="utf-8")

    tool_call_1 = {
        "tool_name": "read_file",
        "payload": {"path": rel_path, "encoding": "utf-8"},
        "allow_write_safe": False,
        "sandbox_roots": [str(sandbox_root_1)],
    }
    tool_call_2 = {
        "tool_name": "read_file",
        "payload": {"path": rel_path, "encoding": "utf-8"},
        "allow_write_safe": False,
        "sandbox_roots": [str(sandbox_root_2)],
    }

    run1_controller = ControllerService(memory_manager=_build_memory_manager(run1_root))
    run2_controller = ControllerService(memory_manager=_build_memory_manager(run2_root))

    run1 = _capture_artifacts(
        run1_root,
        run1_controller,
        user_input="Use a tool to read file",
        tool_call=tool_call_1,
    )
    run2 = _capture_artifacts(
        run2_root,
        run2_controller,
        user_input="Use a tool to read file",
        tool_call=tool_call_2,
    )

    assert run1.workflow_graph == run2.workflow_graph
    assert run1.dag_events == run2.dag_events
    assert run1.task_state == run2.task_state
    assert run1.decisions == run2.decisions
    assert run1.tool_calls == run2.tool_calls


def test_reproducibility_retrieval_integration(
    tmp_path: Path,
    deterministic_runtime: None,
    retrieval_context_builder_patch: None,
) -> None:
    run1_root = tmp_path / "retrieval_run_1"
    run2_root = tmp_path / "retrieval_run_2"

    run1_memory = _build_memory_manager(run1_root)
    run2_memory = _build_memory_manager(run2_root)

    seed_rows = [
        ("python testing reproducibility", {"topic": "testing", "timestamp": "2026-01-01T00:00:00"}),
        ("dag node event ordering deterministic", {"topic": "dag", "timestamp": "2026-01-01T00:00:01"}),
        ("sandbox tool execution contracts", {"topic": "tools", "timestamp": "2026-01-01T00:00:02"}),
    ]
    for text, metadata in seed_rows:
        run1_memory.store_knowledge(text, metadata)
        run2_memory.store_knowledge(text, metadata)

    run1_controller = ControllerService(memory_manager=run1_memory)
    run2_controller = ControllerService(memory_manager=run2_memory)

    user_input = "Find deterministic dag event ordering notes"
    run1 = _capture_artifacts(run1_root, run1_controller, user_input=user_input)
    run2 = _capture_artifacts(run2_root, run2_controller, user_input=user_input)

    assert run1.workflow_graph == run2.workflow_graph
    assert run1.dag_events == run2.dag_events
    assert run1.task_state == run2.task_state
    assert run1.decisions == run2.decisions
    assert run1.tool_calls == run2.tool_calls

    # Retrieval membership comparison is set-based (order may vary).
    assert run1.retrieval_set == run2.retrieval_set


def calculate_reproducibility_score(results: list[bool]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item)
    rate = (passed / total) if total else 0.0
    return {
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "artifact_reproducibility_rate": rate,
        "artifact_target_met": rate == 1.0,
        "generation_exact_match_rate": 0.0,
        "generation_similarity_rate": 0.0,
    }
