import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from backend.memory.episodic_db import EpisodicMemory


def _collect_index_names(db_path: Path) -> set[str]:
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_index_creation_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.db"
    EpisodicMemory(db_path=str(db_path))
    EpisodicMemory(db_path=str(db_path))

    names = _collect_index_names(db_path)

    assert "idx_decisions_task_id" in names
    assert "idx_decisions_action_type" in names
    assert "idx_decisions_id_desc" in names
    assert "idx_tool_calls_decision_id" in names
    assert "idx_tool_calls_tool_name" in names
    assert "idx_tool_calls_id_desc" in names


def test_search_decisions_returns_expected_rows_and_filters_task(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.db"
    memory = EpisodicMemory(db_path=str(db_path))

    memory.log_decision("task-a", "plan", "alpha phase", "queued")
    memory.log_decision("task-a", "plan", "beta phase", "done")
    memory.log_decision("task-b", "plan", "alpha external", "queued")

    task_a_results = memory.search_decisions("alpha", task_id="task-a")

    assert len(task_a_results) == 1
    row = task_a_results[0]
    assert set(row.keys()) == {
        "id",
        "timestamp",
        "task_id",
        "action_type",
        "content",
        "status",
    }
    assert row["task_id"] == "task-a"
    assert "alpha" in row["content"]


def test_search_tool_calls_returns_expected_rows_and_filters_task(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.db"
    memory = EpisodicMemory(db_path=str(db_path))

    d1 = memory.log_decision("task-a", "tool", "decision a", "running")
    d2 = memory.log_decision("task-b", "tool", "decision b", "running")

    memory.log_tool_call(d1, "search", '{"query":"alpha"}', '{"hits":1}')
    memory.log_tool_call(d2, "search", '{"query":"alpha"}', '{"hits":2}')

    task_a_results = memory.search_tool_calls("alpha", task_id="task-a")

    assert len(task_a_results) == 1
    row = task_a_results[0]
    assert set(row.keys()) == {
        "id",
        "decision_id",
        "task_id",
        "tool_name",
        "params",
        "result",
        "timestamp",
    }
    assert row["task_id"] == "task-a"
    assert "alpha" in row["params"]


def test_search_ordering_is_id_desc_and_limit_applies(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.db"
    memory = EpisodicMemory(db_path=str(db_path))

    id_1 = memory.log_decision("task-z", "plan", "alpha one", "queued")
    id_2 = memory.log_decision("task-z", "plan", "alpha two", "queued")
    id_3 = memory.log_decision("task-z", "plan", "alpha three", "queued")

    results = memory.search_decisions("alpha", limit=2)

    assert [row["id"] for row in results] == [id_3, id_2]
    assert len(results) == 2
    assert id_1 not in [row["id"] for row in results]


def test_search_rejects_empty_query_for_both_methods(tmp_path: Path) -> None:
    db_path = tmp_path / "trace.db"
    memory = EpisodicMemory(db_path=str(db_path))

    with pytest.raises(ValueError):
        memory.search_decisions("   ")

    with pytest.raises(ValueError):
        memory.search_tool_calls("")
