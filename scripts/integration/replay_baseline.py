from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.request
from datetime import datetime


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


def _fetch_normalized_dag_events(db_path: str, task_id: str, min_decision_id: int) -> list[dict[str, object]]:
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

    normalized: list[dict[str, object]] = []
    for (content,) in rows:
        payload = json.loads(content)
        normalized.append(
            {
                "event_type": str(payload.get("event_type", "")),
                "node_id": str(payload.get("node_id", "")),
                "node_type": str(payload.get("node_type", "")),
                "controller_state": str(payload.get("controller_state", "")),
                "success": bool(payload.get("success", False)),
            }
        )
    return normalized


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
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read().decode("utf-8", errors="replace")
    return json.loads(payload)


def run_replay_baseline_once() -> dict[str, object]:
    ok, error = _bootstrap_backend()
    if not ok:
        return {"passed": False, "reason": str(error)}

    replay_input = "Replay baseline deterministic check"
    db_path = os.path.join("data", "episodic", "trace.db")
    runs: list[dict[str, object]] = []

    for _ in range(2):
        high_water = _decisions_high_water_mark(db_path)
        task_json = _run_single_task(replay_input)
        task_id = str(task_json.get("task_id", "")).strip()
        if not task_id:
            return {"passed": False, "reason": "missing task_id from /task response"}

        workflow_graph = _load_archived_task_graph(task_id)
        if workflow_graph is None:
            return {"passed": False, "reason": f"missing archived workflow_graph for {task_id}"}

        events = _fetch_normalized_dag_events(db_path, task_id, high_water)
        if not events:
            return {"passed": False, "reason": f"missing dag_node_event rows for {task_id}"}

        runs.append({"task_id": task_id, "workflow_graph": workflow_graph, "events": events})

    run1, run2 = runs
    graph_equal = run1["workflow_graph"] == run2["workflow_graph"]
    events_equal = run1["events"] == run2["events"]
    passed = bool(graph_equal and events_equal)

    result: dict[str, object] = {
        "passed": passed,
        "run_1_task_id": run1["task_id"],
        "run_2_task_id": run2["task_id"],
    }
    if not passed:
        result["run_1_events"] = run1["events"]
        result["run_2_events"] = run2["events"]
    return result


def write_replay_report(result: dict[str, object]) -> str:
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join("reports", f"replay_baseline_report_{timestamp}.txt")
    lines = ["REPLAY BASELINE", "=" * 60]
    if bool(result.get("passed", False)):
        lines.append("REPLAY_BASELINE=PASS")
        lines.append(f"run_1_task_id={result.get('run_1_task_id', '')}")
        lines.append(f"run_2_task_id={result.get('run_2_task_id', '')}")
    else:
        lines.append("REPLAY_BASELINE=FAIL")
        lines.append(f"reason={result.get('reason', 'normalized mismatch')}")
        if "run_1_events" in result:
            lines.append("run_1_events=" + json.dumps(result["run_1_events"], sort_keys=True))
        if "run_2_events" in result:
            lines.append("run_2_events=" + json.dumps(result["run_2_events"], sort_keys=True))

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return report_path


if __name__ == "__main__":
    replay_result = run_replay_baseline_once()
    output_path = write_replay_report(replay_result)
    print(f"Replay report: {output_path}")
    raise SystemExit(0 if bool(replay_result.get("passed", False)) else 1)
