import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from backend.memory.episodic_db import EpisodicMemory


def test_init_creates_tables() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "trace.db"
        EpisodicMemory(db_path=str(db_path))

        with closing(sqlite3.connect(db_path)) as conn:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

    assert "decisions" in names
    assert "tool_calls" in names
    assert "validations" in names


def test_log_decision_inserts_record() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "trace.db"
        memory = EpisodicMemory(db_path=str(db_path))

        decision_id = memory.log_decision(
            task_id="task-1",
            action_type="plan",
            content='{"step": 1}',
            status="pending",
        )

        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT task_id, action_type, content, status FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()

    assert row == ("task-1", "plan", '{"step": 1}', "pending")


def test_log_tool_call_inserts_record() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "trace.db"
        memory = EpisodicMemory(db_path=str(db_path))
        decision_id = memory.log_decision(
            task_id="task-2",
            action_type="tool",
            content='{"tool": "search"}',
            status="running",
        )

        tool_call_id = memory.log_tool_call(
            decision_id=decision_id,
            tool_name="search",
            params='{"query": "x"}',
            result='{"hits": 1}',
        )

        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT decision_id, tool_name, params, result FROM tool_calls WHERE id = ?",
                (tool_call_id,),
            ).fetchone()

    assert row == (decision_id, "search", '{"query": "x"}', '{"hits": 1}')


def test_log_validation_inserts_record() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "trace.db"
        memory = EpisodicMemory(db_path=str(db_path))
        decision_id = memory.log_decision(
            task_id="task-3",
            action_type="validate",
            content='{"check": "schema"}',
            status="done",
        )

        validation_id = memory.log_validation(
            decision_id=decision_id,
            validator_type="schema",
            result="Pass",
            notes="validated",
        )

        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT decision_id, validator_type, result, notes FROM validations WHERE id = ?",
                (validation_id,),
            ).fetchone()

    assert row == (decision_id, "schema", "Pass", "validated")
