from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.request


def _run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True)


def _bootstrap_backend() -> tuple[bool, str | None]:
    steps: list[list[str]] = [
        ["docker", "compose", "config"],
        ["docker", "compose", "build", "backend"],
        ["docker", "compose", "up", "-d", "redis", "backend"],
    ]

    for command in steps:
        proc = _run_command(command)
        if proc.returncode != 0:
            excerpt = ((proc.stderr or "") + (proc.stdout or "")).strip()
            return False, f"{' '.join(command)} :: {' '.join(excerpt.splitlines()[:10])}"

    last_error: str | None = None
    for _ in range(20):
        try:
            with urllib.request.urlopen("http://localhost:8000/health", timeout=15) as response:
                _ = response.read().decode("utf-8", errors="replace")
            last_error = None
            break
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1)

    if last_error is not None:
        return False, f"health check failed: {last_error}"

    return True, None


def _decisions_high_water_mark(db_path: str) -> int:
    if not os.path.exists(db_path):
        return 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM decisions").fetchone()
    return int(row[0]) if row else 0


def _canonicalize_workflow_graph(workflow_graph: dict[str, object]) -> dict[str, object]:
    nodes_raw = workflow_graph.get("nodes")
    edges_raw = workflow_graph.get("edges")
    entry_raw = workflow_graph.get("entry")

    nodes: list[str] = []
    if isinstance(nodes_raw, list):
        nodes = sorted(str(node_id) for node_id in nodes_raw)

    edges: list[dict[str, str]] = []
    if isinstance(edges_raw, list):
        for edge in edges_raw:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("from", ""))
            target = str(edge.get("to", ""))
            edges.append({"from": source, "to": target})
    edges = sorted(edges, key=lambda edge: (edge["from"], edge["to"]))

    return {
        "nodes": nodes,
        "edges": edges,
        "entry": str(entry_raw) if entry_raw is not None else "",
    }


def _fetch_canonical_dag_events(db_path: str, task_id: str, min_decision_id: int) -> list[dict[str, object]]:
    if not os.path.exists(db_path):
        return []

    with sqlite3.connect(db_path) as conn:
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

    canonical: list[dict[str, object]] = []
    for (content,) in rows:
        payload = json.loads(content)
        error_raw = payload.get("error")
        error_code_raw = payload.get("error_code")
        error_present = False
        if isinstance(error_raw, str):
            error_present = bool(error_raw.strip())
        elif error_raw is not None:
            error_present = True

        canonical.append(
            {
                "event_type": str(payload.get("event_type", "")),
                "node_id": str(payload.get("node_id", "")),
                "node_type": str(payload.get("node_type", "")),
                "controller_state": str(payload.get("controller_state", "")),
                "success": bool(payload.get("success", False)),
                "error_present": error_present,
                "error_code": str(error_code_raw).strip() if error_code_raw is not None else "",
            }
        )
    return canonical


def _fetch_controller_latency_baseline(
    db_path: str,
    task_id: str,
    min_decision_id: int,
) -> dict[str, object]:
    if not os.path.exists(db_path):
        return {"total_elapsed_ns": 0, "node_elapsed_ns": {}}

    with sqlite3.connect(db_path) as conn:
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

    total_elapsed_ns = 0
    node_elapsed_ns: dict[str, int] = {}
    for (content,) in rows:
        payload = json.loads(content)
        if str(payload.get("event_type", "")) != "node_end":
            continue

        elapsed_ns_value = payload.get("elapsed_ns")
        if not isinstance(elapsed_ns_value, int):
            continue

        elapsed_ns = max(0, int(elapsed_ns_value))
        total_elapsed_ns += elapsed_ns

        controller_state = str(payload.get("controller_state", ""))
        node_id = str(payload.get("node_id", ""))
        key = f"{controller_state}:{node_id}"
        node_elapsed_ns[key] = int(node_elapsed_ns.get(key, 0) + elapsed_ns)

    return {
        "total_elapsed_ns": int(total_elapsed_ns),
        "node_elapsed_ns": dict(sorted(node_elapsed_ns.items())),
    }


def _int_from_mapping(mapping: object, key: str) -> int:
    if not isinstance(mapping, dict):
        return 0
    value = mapping.get(key)
    return int(value) if isinstance(value, int) else 0


def _load_archived_task_graph(task_id: str) -> dict[str, object] | None:
    archive_path = os.path.join("data", "archives", f"{task_id}.json")
    if not os.path.exists(archive_path):
        return None

    with open(archive_path, "r", encoding="utf-8") as handle:
        task_state = json.load(handle)

    workflow_graph = task_state.get("workflow_graph")
    return workflow_graph if isinstance(workflow_graph, dict) else None


def _run_single_task(user_input: str) -> dict[str, str]:
    task_url = "http://localhost:8000/task"
    request_body = json.dumps({"user_input": user_input}).encode("utf-8")
    request = urllib.request.Request(
        task_url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: str | None = None
    for _ in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read().decode("utf-8", errors="replace")
            return json.loads(payload)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1)

    raise RuntimeError(f"task request failed after retries: {last_error}")


def run_replay_baseline_once() -> dict[str, object]:
    ok, error = _bootstrap_backend()
    if not ok:
        return {"passed": False, "reason": str(error)}

    replay_input = "Replay baseline deterministic check"
    db_path = os.path.join("data", "episodic", "trace.db")
    runs: list[dict[str, object]] = []

    for _ in range(2):
        high_water = _decisions_high_water_mark(db_path)
        try:
            task_json = _run_single_task(replay_input)
        except Exception as exc:
            return {"passed": False, "reason": str(exc)}
        task_id = str(task_json.get("task_id", "")).strip()
        if not task_id:
            return {"passed": False, "reason": "missing task_id from /task response"}

        workflow_graph = _load_archived_task_graph(task_id)
        if workflow_graph is None:
            return {"passed": False, "reason": f"missing archived workflow_graph for {task_id}"}

        canonical_events = _fetch_canonical_dag_events(db_path, task_id, high_water)
        if not canonical_events:
            return {"passed": False, "reason": f"missing dag_node_event rows for {task_id}"}

        canonical_workflow_graph = _canonicalize_workflow_graph(workflow_graph)

        latency_baseline = _fetch_controller_latency_baseline(db_path, task_id, high_water)
        if _int_from_mapping(latency_baseline, "total_elapsed_ns") <= 0:
            return {"passed": False, "reason": f"missing controller latency baseline for {task_id}"}

        runs.append(
            {
                "task_id": task_id,
                "canonical_workflow_graph": canonical_workflow_graph,
                "canonical_events": canonical_events,
                "latency_baseline": latency_baseline,
            }
        )

    run1, run2 = runs
    graph_equal = run1["canonical_workflow_graph"] == run2["canonical_workflow_graph"]
    events_equal = run1["canonical_events"] == run2["canonical_events"]

    run1_total_elapsed_ns = _int_from_mapping(run1.get("latency_baseline"), "total_elapsed_ns")
    run2_total_elapsed_ns = _int_from_mapping(run2.get("latency_baseline"), "total_elapsed_ns")
    latency_delta_ns = abs(run1_total_elapsed_ns - run2_total_elapsed_ns)
    latency_tolerance_ratio = 0.10
    latency_allowed_delta_ns = max(
        2_000_000,
        int(max(run1_total_elapsed_ns, run2_total_elapsed_ns) * latency_tolerance_ratio),
    )
    latency_within_tolerance = latency_delta_ns <= latency_allowed_delta_ns

    passed = bool(graph_equal and events_equal)

    result: dict[str, object] = {
        "passed": passed,
        "run_1_task_id": run1["task_id"],
        "run_2_task_id": run2["task_id"],
        "artifact_compare": {
            "workflow_graph_equal": graph_equal,
            "dag_events_equal": events_equal,
        },
        "controller_latency_baseline": {
            "label": "controller_latency_baseline_total_elapsed_ns",
            "run_1_total_elapsed_ns": run1_total_elapsed_ns,
            "run_2_total_elapsed_ns": run2_total_elapsed_ns,
            "delta_elapsed_ns": latency_delta_ns,
            "allowed_delta_ns": latency_allowed_delta_ns,
            "tolerance_ratio": latency_tolerance_ratio,
            "within_tolerance": latency_within_tolerance,
        },
    }
    if not passed:
        result["run_1_canonical_workflow_graph"] = run1["canonical_workflow_graph"]
        result["run_2_canonical_workflow_graph"] = run2["canonical_workflow_graph"]
        result["run_1_canonical_events"] = run1["canonical_events"]
        result["run_2_canonical_events"] = run2["canonical_events"]
        result["run_1_controller_latency"] = run1["latency_baseline"]
        result["run_2_controller_latency"] = run2["latency_baseline"]
    return result


def test_replay_baseline_same_input_twice_pipeline_artifacts_match() -> None:
    result = run_replay_baseline_once()

    assert bool(result.get("passed", False)), (
        f"Replay baseline mismatch: reason={result.get('reason', '')}; "
        f"artifact_compare={result.get('artifact_compare', '')}; "
        f"controller_latency_baseline={result.get('controller_latency_baseline', '')}; "
        f"run_1_canonical_workflow_graph={result.get('run_1_canonical_workflow_graph', '')}; "
        f"run_2_canonical_workflow_graph={result.get('run_2_canonical_workflow_graph', '')}; "
        f"run_1_canonical_events={result.get('run_1_canonical_events', '')}; "
        f"run_2_canonical_events={result.get('run_2_canonical_events', '')}; "
        f"run_1_controller_latency={result.get('run_1_controller_latency', '')}; "
        f"run_2_controller_latency={result.get('run_2_controller_latency', '')}"
    )
