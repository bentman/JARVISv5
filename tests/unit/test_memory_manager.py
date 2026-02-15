import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from backend.memory.memory_manager import MemoryManager


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def build_manager(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=TestEmbeddingFunction(),
    )


def test_create_task_and_get_task_state() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = build_manager(tmp_dir)
        manager.create_task("task-1", "goal", ["step a", "step b"])

        state = manager.get_task_state("task-1")
        assert state is not None
        assert state["task_id"] == "task-1"
        assert state["goal"] == "goal"


def test_log_decision_and_log_tool_call() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = build_manager(tmp_dir)
        decision_id = manager.log_decision("task-2", "plan", "content", "pending")
        tool_call_id = manager.log_tool_call(decision_id, "search", "{}", "{}")

        assert decision_id > 0
        assert tool_call_id > 0

        with closing(sqlite3.connect(Path(tmp_dir) / "episodic.db")) as conn:
            decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            tool_count = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]

        assert decision_count == 1
        assert tool_count == 1


def test_store_and_retrieve_knowledge() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = build_manager(tmp_dir)
        manager.store_knowledge("alpha memory", {"kind": "alpha"})
        manager.store_knowledge("beta memory", {"kind": "beta"})

        results = manager.retrieve_knowledge("alpha", k=2)
        assert results
        assert "text" in results[0]
        assert "metadata" in results[0]
        assert "score" in results[0]


def test_get_relevant_context_combines_working_and_semantic() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = build_manager(tmp_dir)
        manager.create_task("task-3", "context goal", ["step 1"])
        manager.store_knowledge("context knowledge", {"source": "test"})

        context = manager.get_relevant_context("task-3", "context", k=1)
        assert "working_state" in context
        assert "semantic_results" in context
        assert context["working_state"] is not None
        assert isinstance(context["semantic_results"], list)
