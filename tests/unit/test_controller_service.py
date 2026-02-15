import tempfile
from pathlib import Path

from backend.controller.controller_service import ControllerService
from backend.memory.memory_manager import MemoryManager


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def build_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=TestEmbeddingFunction(),
    )


def test_controller_service_run_task_success_archives() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(memory_manager=build_memory(tmp_dir))
        result = service.run_task(
            task_id="ctrl-task-success",
            goal="controller goal",
            steps=["plan", "execute", "validate"],
            validation_passed=True,
        )

        assert result["final_state"] == "ARCHIVE"
        assert result["archived"] is True


def test_controller_service_run_task_failed_stays_unarchived() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(memory_manager=build_memory(tmp_dir))
        result = service.run_task(
            task_id="ctrl-task-fail",
            goal="controller goal",
            steps=["plan", "execute", "validate"],
            validation_passed=False,
        )

        assert result["final_state"] == "FAILED"
        assert result["archived"] is False
