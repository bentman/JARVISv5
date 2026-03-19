import tempfile
from pathlib import Path
import sys
import types

from backend.memory.memory_manager import MemoryManager
from backend.workflow import (
    ContextBuilderNode,
    LLMWorkerNode,
    RouterNode,
    ValidatorNode,
)
from backend.workflow.nodes.llm_worker_node import _normalize_llm_output
from backend.workflow.nodes.llm_worker_node import _STOP_SEQUENCES


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


def test_router_node_sets_research_intent() -> None:
    node = RouterNode()
    context = {"user_input": "Please research this topic and find sources"}

    result = node.execute(context)
    assert result["intent"] == "research"


def test_router_node_keeps_code_precedence_over_research() -> None:
    node = RouterNode()
    context = {"user_input": "write code and research alternatives"}

    result = node.execute(context)
    assert result["intent"] == "code"


def test_router_node_is_deterministic_for_same_input() -> None:
    node = RouterNode()
    context_a = {"user_input": "find sources about llama.cpp"}
    context_b = {"user_input": "find sources about llama.cpp"}

    result_a = node.execute(context_a)
    result_b = node.execute(context_b)
    assert result_a["intent"] == "research"
    assert result_b["intent"] == "research"


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


def test_llm_worker_node_preserves_multiline_output(monkeypatch) -> None:
    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(
            self,
            prompt: str,
            max_tokens: int = 100,
            echo: bool = False,
            stop: list[str] | None = None,
        ) -> dict:
            return {
                "choices": [
                    {
                        "text": "```python\nprint('abc123XYZ789')\n```\n"
                    }
                ]
            }

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "write a python snippet to produce a 12 character random alphanumeric",
            "llm_model_path": TEST_MODEL_PATH,
        }
    )

    assert result["llm_output"] == "```python\nprint('abc123XYZ789')\n```"


def test_llm_worker_node_passes_seed_when_present(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "seeded"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "hello",
            "llm_model_path": TEST_MODEL_PATH,
            "generation_seed": 42,
        }
    )

    assert result["llm_output"] == "seeded"
    assert captured.get("seed") == 42


def test_llm_worker_node_omits_seed_when_absent(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "unseeded"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "hello",
            "llm_model_path": TEST_MODEL_PATH,
        }
    )

    assert result["llm_output"] == "unseeded"
    assert "seed" not in captured


def test_llm_worker_uses_context_messages_when_present(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "message path ok"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "fallback input",
            "llm_model_path": TEST_MODEL_PATH,
            "messages": [
                {"role": "system", "content": "system context"},
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
                {"role": "user", "content": "second question"},
            ],
        }
    )

    prompt = str(captured.get("prompt", ""))
    assert "System: system context" in prompt
    assert "User: first question" in prompt
    assert "Assistant: first answer" in prompt
    assert "User: second question" in prompt
    assert prompt.rstrip().endswith("Assistant:")
    assert "User: fallback input" not in prompt
    assert result["llm_output"] == "message path ok"


def test_llm_worker_falls_back_to_single_turn_when_messages_absent(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "fallback ok"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "single-turn input",
            "llm_model_path": TEST_MODEL_PATH,
        }
    )

    prompt = str(captured.get("prompt", ""))
    assert "User: single-turn input" in prompt
    assert prompt.rstrip().endswith("Assistant:")
    assert result["llm_output"] == "fallback ok"


def test_llm_worker_preserves_seed_stop_and_normalization_with_messages(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "<|assistant|> OK\nUser: continue"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "ignored because messages present",
            "llm_model_path": TEST_MODEL_PATH,
            "generation_seed": 123,
            "messages": [
                {"role": "system", "content": "seeded system context"},
                {"role": "user", "content": "seeded user query"},
            ],
        }
    )

    assert captured.get("seed") == 123
    assert captured.get("stop") == list(_STOP_SEQUENCES)
    assert result["llm_output"] == "OK"


def test_llm_worker_redacts_message_history_prompt_when_enabled(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "redacted path ok"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "fallback input",
            "llm_model_path": TEST_MODEL_PATH,
            "redact_pii_queries": True,
            "messages": [
                {"role": "system", "content": "system context"},
                {"role": "user", "content": "email me at test@example.com"},
                {"role": "assistant", "content": "my backup is second@example.com"},
            ],
        }
    )

    prompt = str(captured.get("prompt", ""))
    assert "User: email me at test@example.com" not in prompt
    assert "Assistant: my backup is second@example.com" not in prompt
    assert "[EMAIL_REDACTED]" in prompt
    assert result["llm_output"] == "redacted path ok"


def test_llm_worker_message_history_prompt_unchanged_when_redaction_disabled(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "raw path ok"}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    node = LLMWorkerNode()
    result = node.execute(
        {
            "user_input": "fallback input",
            "llm_model_path": TEST_MODEL_PATH,
            "redact_pii_queries": False,
            "messages": [
                {"role": "system", "content": "system context"},
                {"role": "user", "content": "email me at test@example.com"},
                {"role": "assistant", "content": "my backup is second@example.com"},
            ],
        }
    )

    prompt = str(captured.get("prompt", ""))
    assert "User: email me at test@example.com" in prompt
    assert "Assistant: my backup is second@example.com" in prompt
    assert "[EMAIL_REDACTED]" not in prompt
    assert result["llm_output"] == "raw path ok"


def test_validator_node_marks_context_valid_for_substantive_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": "This is valid output."})

    assert result["is_valid"] is True
    assert result["validation_status"] == "passed"
    assert result["validation_errors"] == []


def test_validator_node_marks_context_invalid_for_empty_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": ""})

    assert result["is_valid"] is False
    assert result["validation_status"] == "failed"
    assert result["validation_errors"] == ["empty_output"]


def test_validator_node_marks_context_invalid_for_too_short_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": "short"})

    assert result["is_valid"] is False
    assert result["validation_status"] == "failed"
    assert result["validation_errors"] == ["too_short"]


def test_validator_node_marks_context_invalid_for_model_error_output() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": "Local model missing. Please configure it."})

    assert result["is_valid"] is False
    assert result["validation_status"] == "failed"
    assert result["validation_errors"] == ["model_error_output"]


def test_validator_node_marks_context_invalid_for_explicit_llm_error() -> None:
    node = ValidatorNode()
    result = node.execute({"llm_output": "This is valid output.", "llm_error": "llama_cpp_import_error"})

    assert result["is_valid"] is False
    assert result["validation_status"] == "failed"
    assert result["validation_errors"] == ["explicit_llm_error"]


def test_validator_node_is_deterministic_for_same_input() -> None:
    node = ValidatorNode()
    context_a = {"llm_output": "short"}
    context_b = {"llm_output": "short"}

    result_a = node.execute(context_a)
    result_b = node.execute(context_b)

    assert result_a["is_valid"] is False
    assert result_b["is_valid"] is False
    assert result_a["validation_status"] == "failed"
    assert result_b["validation_status"] == "failed"
    assert result_a["validation_errors"] == ["too_short"]
    assert result_b["validation_errors"] == ["too_short"]


def test_normalize_llm_output_removes_assistant_prefix_token() -> None:
    raw = "<|assistant|> OK"
    assert _normalize_llm_output(raw) == "OK"


def test_normalize_llm_output_truncates_at_next_speaker_marker() -> None:
    raw = "OK\nUser: continue"
    assert _normalize_llm_output(raw) == "OK"


def test_normalize_llm_output_strict_exact_short_answer_on_continuation() -> None:
    raw = "OK\n\nNow, in the context of a more complex scenario:"
    assert _normalize_llm_output(raw) == "OK"


def test_normalize_llm_output_strips_assistant_token_and_truncates_on_user_marker() -> None:
    raw = "<|assistant|>\nOK\n\nUser: continue"
    assert _normalize_llm_output(raw) == "OK"


def test_llm_worker_stop_sequences_include_required_boundaries() -> None:
    required = {"\nUser:", "\nAssistant:", "<|user|>", "<|assistant|>"}
    assert required.issubset(set(_STOP_SEQUENCES))
