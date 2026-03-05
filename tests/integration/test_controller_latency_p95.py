from __future__ import annotations

"""
Controller Latency P95 (Project.md §10.2 / Task 10.5)

Protocol:
- Uses only existing controller/DAG timing artifacts (`elapsed_ns`, `start_offset_ns`)
  persisted in episodic `dag_node_event` records.
- Warm-up runs are executed and excluded from measured percentiles.
- Percentiles are reported in ms; p95 is the gate metric.

Inference isolation:
- No dedicated `llm_inference_ns` artifact exists in repository timing output.
- Deterministic proxy used: `EXECUTE:llm_worker` node `elapsed_ns` sum.
- Controller overhead formula:
    controller_overhead_ns = max(0, total_elapsed_ns - llm_inference_ns_proxy)

FSM transition overhead note:
- There is no direct per-transition elapsed timing artifact for FSM transitions.
- The FSM overhead sub-test is intentionally skipped with explicit reason.
"""

import json
import sqlite3
import statistics
import time
from pathlib import Path
from typing import Any

import pytest

from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager
from backend.models.model_registry import ModelRegistry


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


def _build_controller(root: Path) -> ControllerService:
    memory = _build_memory_manager(root)
    # Standard configuration object; empty catalog path avoids model fetch/network side effects.
    registry = ModelRegistry(catalog_path=str(root / "models.none.yaml"))
    return ControllerService(memory_manager=memory, model_registry=registry)


def _decisions_high_water_mark(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM decisions").fetchone()
    return int(row[0]) if row else 0


def _fetch_dag_events(db_path: Path, task_id: str, min_decision_id: int) -> list[dict[str, Any]]:
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

    events: list[dict[str, Any]] = []
    for (content,) in rows:
        payload = json.loads(str(content))
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _latency_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    total_elapsed_ns = 0
    node_elapsed_ns: dict[str, int] = {}
    min_start_ns: int | None = None
    max_end_ns: int | None = None

    for event in events:
        event_type = str(event.get("event_type", ""))
        node_id = str(event.get("node_id", ""))
        controller_state = str(event.get("controller_state", ""))
        elapsed_ns = event.get("elapsed_ns")
        start_offset_ns = event.get("start_offset_ns")

        if isinstance(start_offset_ns, int):
            start_clamped = max(0, int(start_offset_ns))
            if min_start_ns is None or start_clamped < min_start_ns:
                min_start_ns = start_clamped

        if event_type != "node_end" or not isinstance(elapsed_ns, int):
            continue

        elapsed_clamped = max(0, int(elapsed_ns))
        total_elapsed_ns += elapsed_clamped
        key = f"{controller_state}:{node_id}"
        node_elapsed_ns[key] = int(node_elapsed_ns.get(key, 0) + elapsed_clamped)

        if isinstance(start_offset_ns, int):
            end_ns = max(0, int(start_offset_ns)) + elapsed_clamped
            if max_end_ns is None or end_ns > max_end_ns:
                max_end_ns = end_ns

    llm_inference_ns_proxy = int(node_elapsed_ns.get("EXECUTE:llm_worker", 0))
    controller_overhead_ns = max(0, int(total_elapsed_ns) - llm_inference_ns_proxy)

    dag_wall_ns = 0
    if min_start_ns is not None and max_end_ns is not None and max_end_ns >= min_start_ns:
        dag_wall_ns = int(max_end_ns - min_start_ns)

    # DAG dispatch/scheduling overhead is scoped to EXECUTE-phase node timeline
    # to avoid counting non-DAG controller bookkeeping between PLAN/VALIDATE/COMMIT.
    execute_min_start_ns: int | None = None
    execute_max_end_ns: int | None = None
    execute_elapsed_ns_sum = 0
    for event in events:
        state = str(event.get("controller_state", ""))
        if state != "EXECUTE":
            continue
        event_type = str(event.get("event_type", ""))
        start_offset_ns = event.get("start_offset_ns")
        elapsed_ns = event.get("elapsed_ns")

        if event_type == "node_start" and isinstance(start_offset_ns, int):
            start = max(0, int(start_offset_ns))
            if execute_min_start_ns is None or start < execute_min_start_ns:
                execute_min_start_ns = start

        if event_type == "node_end" and isinstance(start_offset_ns, int) and isinstance(elapsed_ns, int):
            start = max(0, int(start_offset_ns))
            elapsed = max(0, int(elapsed_ns))
            end = start + elapsed
            if execute_max_end_ns is None or end > execute_max_end_ns:
                execute_max_end_ns = end
            execute_elapsed_ns_sum += elapsed

    execute_window_ns = 0
    if (
        execute_min_start_ns is not None
        and execute_max_end_ns is not None
        and execute_max_end_ns >= execute_min_start_ns
    ):
        execute_window_ns = int(execute_max_end_ns - execute_min_start_ns)

    dag_dispatch_overhead_ns = max(0, int(execute_window_ns) - int(execute_elapsed_ns_sum))

    return {
        "total_elapsed_ns": int(total_elapsed_ns),
        "node_elapsed_ns": dict(sorted(node_elapsed_ns.items())),
        "llm_inference_ns_proxy": int(llm_inference_ns_proxy),
        "controller_overhead_ns": int(controller_overhead_ns),
        "dag_wall_ns": int(dag_wall_ns),
        "execute_window_ns": int(execute_window_ns),
        "execute_elapsed_ns_sum": int(execute_elapsed_ns_sum),
        "dag_dispatch_overhead_ns": int(dag_dispatch_overhead_ns),
    }


def _ns_to_ms(ns: int) -> float:
    return float(ns) / 1_000_000.0


def _percentiles_ms(samples_ms: list[float]) -> dict[str, float]:
    if len(samples_ms) < 2:
        raise AssertionError("percentile calculation requires at least two samples")
    p50 = float(statistics.median(samples_ms))
    p95 = float(statistics.quantiles(samples_ms, n=20)[18])
    p99 = float(statistics.quantiles(samples_ms, n=100)[98])
    return {"p50": p50, "p95": p95, "p99": p99}


def _run_controller_with_latency(controller: ControllerService, db_path: Path, user_input: str) -> dict[str, Any]:
    high_water = _decisions_high_water_mark(db_path)
    result = controller.run(user_input=user_input)
    assert bool(result.get("archived", False)), f"run did not archive: {result}"
    task_id = str(result.get("task_id", "")).strip()
    assert task_id, "missing task_id"
    events = _fetch_dag_events(db_path, task_id, high_water)
    assert events, f"missing dag events for {task_id}"
    return _latency_from_events(events)


def test_controller_latency_p95_cold_start(tmp_path: Path) -> None:
    warmup_runs = 10
    measured_runs = 120
    overhead_samples_ms: list[float] = []

    for idx in range(warmup_runs + measured_runs):
        run_root = tmp_path / "cold_start" / f"run_{idx}"
        controller = _build_controller(run_root)
        db_path = run_root / "episodic" / "trace.db"
        metrics = _run_controller_with_latency(
            controller,
            db_path,
            user_input=f"Cold-start latency sample {idx}",
        )
        if idx >= warmup_runs:
            overhead_samples_ms.append(_ns_to_ms(int(metrics["controller_overhead_ns"])))

    pct = _percentiles_ms(overhead_samples_ms)
    assert pct["p95"] < 200.0, f"Cold-start controller overhead p95={pct['p95']:.3f}ms >= 200ms"


def test_controller_latency_p95_warm_cache(tmp_path: Path) -> None:
    warmup_runs = 10
    measured_runs = 120
    root = tmp_path / "warm_cache"
    controller = _build_controller(root)
    db_path = root / "episodic" / "trace.db"
    overhead_samples_ms: list[float] = []

    user_input = "Warm-cache latency benchmark prompt"
    for idx in range(warmup_runs + measured_runs):
        metrics = _run_controller_with_latency(controller, db_path, user_input=user_input)
        if idx >= warmup_runs:
            overhead_samples_ms.append(_ns_to_ms(int(metrics["controller_overhead_ns"])))

    pct = _percentiles_ms(overhead_samples_ms)
    assert pct["p95"] < 200.0, f"Warm-cache controller overhead p95={pct['p95']:.3f}ms >= 200ms"


def test_fsm_transition_overhead() -> None:
    pytest.skip(
        "No direct per-transition elapsed timing artifact exists for FSM transitions; "
        "task skips until explicit transition-duration telemetry is available."
    )


def test_dag_execution_overhead(tmp_path: Path) -> None:
    warmup_runs = 5
    measured_runs = 60
    root = tmp_path / "dag_overhead"
    controller = _build_controller(root)
    db_path = root / "episodic" / "trace.db"
    overhead_samples_ms: list[float] = []

    for idx in range(warmup_runs + measured_runs):
        metrics = _run_controller_with_latency(
            controller,
            db_path,
            user_input=f"DAG-overhead sample {idx}",
        )
        if idx >= warmup_runs:
            overhead_samples_ms.append(_ns_to_ms(int(metrics["dag_dispatch_overhead_ns"])))

    pct = _percentiles_ms(overhead_samples_ms)
    assert pct["p95"] < 50.0, f"DAG dispatch overhead p95={pct['p95']:.3f}ms >= 50ms"


def test_memory_access_latency(tmp_path: Path) -> None:
    root = tmp_path / "memory_latency"
    memory = _build_memory_manager(root)

    task_id = "memory-latency-task"
    memory.create_task(task_id, "memory benchmark", ["PLAN", "EXECUTE", "VALIDATE", "COMMIT", "ARCHIVE"])

    working_write_ms: list[float] = []
    working_read_ms: list[float] = []
    for idx in range(120):
        t0 = time.perf_counter_ns()
        memory.append_task_message(task_id, "assistant", f"msg-{idx}", max_messages=50)
        t1 = time.perf_counter_ns()
        _ = memory.get_task_state(task_id)
        t2 = time.perf_counter_ns()
        working_write_ms.append(_ns_to_ms(t1 - t0))
        working_read_ms.append(_ns_to_ms(t2 - t1))

    episodic_ms: list[float] = []
    for idx in range(120):
        t0 = time.perf_counter_ns()
        decision_id = memory.log_decision(
            task_id=task_id,
            action_type="latency_probe",
            content=json.dumps({"idx": idx}, sort_keys=True),
            status="ok",
        )
        memory.log_tool_call(
            decision_id=decision_id,
            tool_name="noop",
            params=json.dumps({"idx": idx}, sort_keys=True),
            result=json.dumps({"ok": True}, sort_keys=True),
        )
        t1 = time.perf_counter_ns()
        episodic_ms.append(_ns_to_ms(t1 - t0))

    for idx in range(1000):
        memory.store_knowledge(f"semantic-seed-{idx}", {"i": idx, "bucket": idx % 10})

    semantic_ms: list[float] = []
    for idx in range(120):
        t0 = time.perf_counter_ns()
        _ = memory.semantic.search_text(f"semantic-seed-{idx % 1000}", top_k=10)
        t1 = time.perf_counter_ns()
        semantic_ms.append(_ns_to_ms(t1 - t0))

    working_p95 = max(
        _percentiles_ms(working_write_ms)["p95"],
        _percentiles_ms(working_read_ms)["p95"],
    )
    episodic_p95 = _percentiles_ms(episodic_ms)["p95"]
    semantic_p95 = _percentiles_ms(semantic_ms)["p95"]

    assert working_p95 < 10.0, f"Working-state p95={working_p95:.3f}ms >= 10ms"
    assert episodic_p95 < 20.0, f"Episodic p95={episodic_p95:.3f}ms >= 20ms"
    assert semantic_p95 < 100.0, f"Semantic retrieval p95={semantic_p95:.3f}ms >= 100ms"
