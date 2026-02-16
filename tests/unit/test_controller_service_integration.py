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


def test_controller_service_run_executes_nodes_and_handles_llm_gracefully() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(memory_manager=build_memory(tmp_dir))

        result = service.run(user_input="test code")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        assert "context" in result

        context = result["context"]
        assert context.get("intent") == "code"
        assert "llm_output" in context
        assert isinstance(context["llm_output"], str)
        assert context["llm_output"].strip() != ""
