import tempfile
from pathlib import Path

from backend.memory.memory_manager import MemoryManager
from backend.workflow import (
    ContextBuilderNode,
    LLMWorkerNode,
    RouterNode,
    ValidatorNode,
)


TEST_MODEL_PATH = "models/test-model.gguf"


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


def test_router_node_sets_code_intent() -> None:
    node = RouterNode()
    context = {"user_input": "please write code for me"}

    result = node.execute(context)
    assert result["intent"] == "code"


def test_router_node_sets_chat_intent() -> None:
    node = RouterNode()
    context = {"user_input": "hello how are you"}

    result = node.execute(context)
    assert result["intent"] == "chat"


def test_context_builder_node_adds_working_state() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = build_memory(tmp_dir)
        memory.create_task("node-task", "node goal", ["step a"])

        node = ContextBuilderNode()
        context = {
            "memory_manager": memory,
            "task_id": "node-task",
        }
        result = node.execute(context)

        assert result["working_state"] is not None
        assert result["working_state"]["task_id"] == "node-task"


def test_context_builder_node_handles_missing_memory_manager() -> None:
    node = ContextBuilderNode()
    context = {"task_id": "missing-memory"}

    result = node.execute(context)
    assert result["working_state"] is None
    assert result["context_builder_error"] == "memory_manager_missing"


def test_llm_worker_node_imports_llama_cpp_and_handles_missing_model() -> None:
    node = LLMWorkerNode()
    context = {
        "user_input": "Hello from test",
        "llm_model_path": TEST_MODEL_PATH,
    }

    result = node.execute(context)

    assert result["llm_model_path"] == TEST_MODEL_PATH
    assert "llm_output" in result
    assert isinstance(result["llm_output"], str)

    if result.get("llm_imported") is False:
        assert "llm_error" in result
        assert str(result["llm_error"]).startswith("llama_cpp_import_error")
        return

    assert result["llm_imported"] is True

    if result["llm_output"] == "":
        assert "llm_error" in result


def test_llm_worker_node_handles_missing_model_path() -> None:
    node = LLMWorkerNode()
    result = node.execute({"user_input": "Hello from test"})

    assert result["llm_error"] == "llm_model_path_missing"


def test_validator_node_marks_context_valid_for_non_empty_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": "some output"})

    assert result["is_valid"] is True


def test_validator_node_marks_context_invalid_for_empty_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": ""})

    assert result["is_valid"] is False
