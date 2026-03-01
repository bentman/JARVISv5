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

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_task_id ON decisions(task_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_action_type ON decisions(action_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_id_desc ON decisions(id DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_calls_decision_id ON tool_calls(decision_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name ON tool_calls(tool_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_calls_id_desc ON tool_calls(id DESC)"
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

    def search_decisions(
        self,
        query: str,
        *,
        limit: int = 20,
        task_id: str | None = None,
    ) -> list[dict]:
        query_text = query.strip()
        if not query_text:
            raise ValueError("query must be non-empty")

        limit_int = int(limit)
        if limit_int < 1:
            raise ValueError("limit must be >= 1")

        like_query = f"%{query_text}%"
        sql = """
            SELECT id, timestamp, task_id, action_type, content, status
            FROM decisions
            WHERE (
                content LIKE ? OR
                action_type LIKE ? OR
                status LIKE ?
            )
        """
        params: list[object] = [like_query, like_query, like_query]
        if task_id is not None:
            sql += " AND task_id = ?"
            params.append(task_id)

        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit_int)

        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "id": int(row[0]),
                "timestamp": row[1],
                "task_id": row[2],
                "action_type": row[3],
                "content": row[4],
                "status": row[5],
            }
            for row in rows
        ]

    def search_tool_calls(
        self,
        query: str,
        *,
        limit: int = 20,
        task_id: str | None = None,
    ) -> list[dict]:
        query_text = query.strip()
        if not query_text:
            raise ValueError("query must be non-empty")

        limit_int = int(limit)
        if limit_int < 1:
            raise ValueError("limit must be >= 1")

        like_query = f"%{query_text}%"
        sql = """
            SELECT tc.id, tc.decision_id, d.task_id, tc.tool_name, tc.params, tc.result, tc.timestamp
            FROM tool_calls tc
            INNER JOIN decisions d ON d.id = tc.decision_id
            WHERE (
                tc.tool_name LIKE ? OR
                tc.params LIKE ? OR
                tc.result LIKE ?
            )
        """
        params: list[object] = [like_query, like_query, like_query]
        if task_id is not None:
            sql += " AND d.task_id = ?"
            params.append(task_id)

        sql += " ORDER BY tc.id DESC LIMIT ?"
        params.append(limit_int)

        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "id": int(row[0]),
                "decision_id": int(row[1]),
                "task_id": row[2],
                "tool_name": row[3],
                "params": row[4],
                "result": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]
