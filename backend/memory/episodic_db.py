import os
import sqlite3
from contextlib import closing
from datetime import datetime


class EpisodicMemory:
    def __init__(self, db_path: str = "data/episodic/trace.db") -> None:
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    params TEXT NOT NULL,
                    result TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES decisions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id INTEGER NOT NULL,
                    validator_type TEXT NOT NULL,
                    result TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    FOREIGN KEY(decision_id) REFERENCES decisions(id)
                )
                """
            )

            conn.commit()

    def log_decision(self, task_id: str, action_type: str, content: str, status: str) -> int:
        timestamp = datetime.utcnow().isoformat()
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO decisions (timestamp, task_id, action_type, content, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, task_id, action_type, content, status),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert decision record")
            return int(cursor.lastrowid)

    def log_tool_call(self, decision_id: int, tool_name: str, params: str, result: str) -> int:
        timestamp = datetime.utcnow().isoformat()
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tool_calls (decision_id, tool_name, params, result, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (decision_id, tool_name, params, result, timestamp),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert tool call record")
            return int(cursor.lastrowid)

    def log_validation(self, decision_id: int, validator_type: str, result: str, notes: str) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO validations (decision_id, validator_type, result, notes)
                VALUES (?, ?, ?, ?)
                """,
                (decision_id, validator_type, result, notes),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert validation record")
            return int(cursor.lastrowid)
