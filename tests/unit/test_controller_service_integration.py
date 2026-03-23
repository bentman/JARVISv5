import json
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

import backend.security.audit_logger as audit_logger_module
import backend.controller.controller_service as controller_service_module
from backend.controller.controller_service import ControllerService
from backend.security.audit_logger import SecurityAuditLogger
from backend.workflow.dag_executor import DAGExecutor
from backend.memory.memory_manager import MemoryManager
from backend.models.escalation_policy import EscalationProviderBase
from backend.models.hardware_profiler import HardwareService, HardwareType
from backend.models.model_registry import ModelRegistry


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


class RecordingMemoryManager(MemoryManager):
    def __init__(
        self,
        episodic_db_path: str,
        working_base_path: str,
        working_archive_path: str,
        semantic_db_path: str,
        embedding_model: TestEmbeddingFunction,
    ) -> None:
        super().__init__(
            episodic_db_path=episodic_db_path,
            working_base_path=working_base_path,
            working_archive_path=working_archive_path,
            semantic_db_path=semantic_db_path,
            embedding_model=embedding_model,
        )
        self.semantic_writes: list[dict] = []

    def store_knowledge(self, text: str, metadata: dict[str, object]) -> int:
        self.semantic_writes.append({"text": text, "metadata": dict(metadata)})
        return super().store_knowledge(text, metadata)


def build_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=TestEmbeddingFunction(),
    )


def build_recording_memory(tmp_dir: str) -> RecordingMemoryManager:
    base = Path(tmp_dir)
    return RecordingMemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=TestEmbeddingFunction(),
    )


class StubHardwareService(HardwareService):
    def detect_hardware_type(self) -> HardwareType:
        return HardwareType.CPU_ONLY

    def get_hardware_profile(self) -> str:
        return "light"


class StubModelRegistry(ModelRegistry):
    def __init__(self) -> None:
        self.models = []

    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        return None


class StubSTTModelRegistry(StubModelRegistry):
    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        _ = profile
        _ = hardware
        if role != "stt":
            return None
        return {"id": "whisper-base", "model_dir": "models/faster-whisper-base"}

    def ensure_model_present(self, model: dict) -> str:
        _ = model
        return "models/faster-whisper-base"


class StubTTSModelRegistry(StubModelRegistry):
    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        _ = profile
        _ = hardware
        if role == "tts":
            return {"id": "piper-tts", "path": "models/en_US-lessac-medium.onnx"}
        if role == "tts-config":
            return {"id": "piper-tts-config", "path": "models/en_US-lessac-medium.onnx.json"}
        return None

    def ensure_model_present(self, model: dict) -> str:
        model_id = str(model.get("id", ""))
        if model_id == "piper-tts":
            return "models/en_US-lessac-medium.onnx"
        if model_id == "piper-tts-config":
            return "models/en_US-lessac-medium.onnx.json"
        raise RuntimeError("unexpected_model")


class StubTTSMissingConfigRegistry(StubModelRegistry):
    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        _ = profile
        _ = hardware
        if role == "tts":
            return {"id": "piper-tts", "path": "models/en_US-lessac-medium.onnx"}
        if role == "tts-config":
            return None
        return None


class PresentModelRegistry(StubModelRegistry):
    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        _ = profile
        _ = hardware
        _ = role
        return {"id": "local-model", "path": "models/local.gguf"}

    def ensure_model_present(self, model: dict) -> str:
        _ = model
        return "models/local.gguf"


class MissingModelPathRegistry(StubModelRegistry):
    def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
        _ = profile
        _ = hardware
        _ = role
        return {"id": "local-model", "path": "models/missing.gguf"}

    def ensure_model_present(self, model: dict) -> str:
        _ = model
        raise RuntimeError("missing local model file")


class StubEscalationProvider(EscalationProviderBase):
    def __init__(self, *, ok: bool, output: str, error: str = "") -> None:
        self.name = "stub"
        self.ok = ok
        self.output = output
        self.error = error
        self.last_prompt = ""

    def execute(self, prompt: str, max_tokens: int, seed: int | None) -> tuple[bool, str, str]:
        _ = max_tokens
        _ = seed
        self.last_prompt = prompt
        return self.ok, self.output, self.error


def test_controller_escalation_registry_is_populated_with_real_providers() -> None:
    registry = controller_service_module._ESCALATION_PROVIDER_REGISTRY

    assert set(registry.keys()) == {"anthropic", "openai", "gemini", "grok"}
    assert isinstance(registry["anthropic"], EscalationProviderBase)
    assert isinstance(registry["openai"], EscalationProviderBase)
    assert isinstance(registry["gemini"], EscalationProviderBase)
    assert isinstance(registry["grok"], EscalationProviderBase)


def test_controller_service_run_executes_nodes_and_handles_llm_gracefully() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="test code")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        assert "context" in result

        context = result["context"]
        assert context.get("intent") == "code"
        assert context.get("selected_model") is None
        assert context.get("llm_model_path") == ""

        assert "llm_output" in context
        assert isinstance(context["llm_output"], str)
        assert "Local model missing" in context["llm_output"]


def test_controller_semantic_write_occurs_once_on_successful_validated_flow(monkeypatch) -> None:
    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode
    from backend.workflow.nodes.validator_node import ValidatorNode

    expected_output = "This is a sufficiently long assistant response for semantic memory persistence."

    def _stub_llm_execute(self, context: dict) -> dict:
        _ = self
        context["llm_output"] = expected_output
        context["llm_stream_chunks"] = [expected_output]
        return context

    def _stub_validator_execute(self, context: dict) -> dict:
        _ = self
        context["is_valid"] = True
        context["validation_status"] = "passed"
        context["validation_errors"] = []
        return context

    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute)
    monkeypatch.setattr(ValidatorNode, "execute", _stub_validator_execute)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="persist semantic output")

        assert result["final_state"] == "ARCHIVE"
        assert len(memory.semantic_writes) == 1

        write = memory.semantic_writes[0]
        assert write["text"] == expected_output
        assert write["metadata"]["task_id"] == result["task_id"]
        assert write["metadata"]["source"] == "assistant_final"
        assert write["metadata"]["intent"] == "chat"
        assert write["metadata"]["final_state_hint"] == "validated"


def test_controller_semantic_write_skips_invalid_and_empty_paths(monkeypatch) -> None:
    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode
    from backend.workflow.nodes.validator_node import ValidatorNode

    def _stub_llm_execute_long(self, context: dict) -> dict:
        _ = self
        context["llm_output"] = "This is long enough but should not persist when validation fails."
        context["llm_stream_chunks"] = [context["llm_output"]]
        return context

    def _stub_llm_execute_empty(self, context: dict) -> dict:
        _ = self
        context["llm_output"] = "   "
        context["llm_stream_chunks"] = [context["llm_output"]]
        return context

    def _stub_validator_fail(self, context: dict) -> dict:
        _ = self
        context["is_valid"] = False
        context["validation_status"] = "failed"
        context["validation_errors"] = ["forced_invalid"]
        return context

    def _stub_validator_pass(self, context: dict) -> dict:
        _ = self
        context["is_valid"] = True
        context["validation_status"] = "passed"
        context["validation_errors"] = []
        return context

    # Case A: validation fails -> no semantic write.
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute_long)
    monkeypatch.setattr(ValidatorNode, "execute", _stub_validator_fail)
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="invalid flow")

        assert result["final_state"] == "FAILED"
        assert memory.semantic_writes == []

    # Case B: validation passes but output empty -> no semantic write.
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute_empty)
    monkeypatch.setattr(ValidatorNode, "execute", _stub_validator_pass)
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="empty output flow")

        assert result["final_state"] == "ARCHIVE"
        assert memory.semantic_writes == []


def test_controller_result_redaction_enabled_redacts_persisted_assistant_and_semantic_write(monkeypatch) -> None:
    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode
    from backend.workflow.nodes.validator_node import ValidatorNode

    class _Settings:
        REDACT_PII_RESULTS = True

    pii_output = "Contact me at test@example.com for updates and follow-up details."

    def _stub_llm_execute(self, context: dict) -> dict:
        _ = self
        context["llm_output"] = pii_output
        context["llm_stream_chunks"] = [pii_output]
        return context

    def _stub_validator_execute(self, context: dict) -> dict:
        _ = self
        context["is_valid"] = True
        context["validation_status"] = "passed"
        context["validation_errors"] = []
        return context

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute)
    monkeypatch.setattr(ValidatorNode, "execute", _stub_validator_execute)

    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="redact result output")

        assert result["final_state"] == "ARCHIVE"

        task_state = memory.get_task_state(result["task_id"])
        assert isinstance(task_state, dict)
        messages = task_state.get("messages", [])
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        assert assistant_messages
        persisted_assistant = str(assistant_messages[-1].get("content", ""))
        assert "test@example.com" not in persisted_assistant
        assert "[EMAIL_REDACTED]" in persisted_assistant

        assert len(memory.semantic_writes) == 1
        semantic_text = str(memory.semantic_writes[0].get("text", ""))
        assert "test@example.com" not in semantic_text
        assert "[EMAIL_REDACTED]" in semantic_text


def test_controller_result_redaction_disabled_preserves_persisted_assistant_output(monkeypatch) -> None:
    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode
    from backend.workflow.nodes.validator_node import ValidatorNode

    class _Settings:
        REDACT_PII_RESULTS = False

    pii_output = "Contact me at test@example.com for updates and follow-up details."

    def _stub_llm_execute(self, context: dict) -> dict:
        _ = self
        context["llm_output"] = pii_output
        context["llm_stream_chunks"] = [pii_output]
        return context

    def _stub_validator_execute(self, context: dict) -> dict:
        _ = self
        context["is_valid"] = True
        context["validation_status"] = "passed"
        context["validation_errors"] = []
        return context

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute)
    monkeypatch.setattr(ValidatorNode, "execute", _stub_validator_execute)

    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="do not redact result output")

        assert result["final_state"] == "ARCHIVE"

        task_state = memory.get_task_state(result["task_id"])
        assert isinstance(task_state, dict)
        messages = task_state.get("messages", [])
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        assert assistant_messages
        persisted_assistant = str(assistant_messages[-1].get("content", ""))
        assert persisted_assistant == pii_output


def test_controller_local_model_found_sets_escalation_not_attempted(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "stub"
        ESCALATION_BUDGET_USD = 5.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="hello")
        context = result["context"]

        assert context.get("escalation_status") == "not_attempted"
        assert context.get("llm_model_path") == "models/local.gguf"


def test_controller_escalation_denied_preserves_fallback(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="code help")
        context = result["context"]

        assert context.get("escalation_status") == "denied"
        assert context.get("escalation_code") == "permission_denied"
        assert isinstance(context.get("escalation_reason"), str)
        assert context.get("skip_llm") is True
        assert "Local model missing" in str(context.get("llm_output", ""))


def test_controller_escalation_denied_when_provider_empty(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="code help")
        context = result["context"]

        assert context.get("escalation_status") == "denied"
        assert context.get("escalation_code") == "provider_not_configured"
        assert isinstance(context.get("escalation_reason"), str)
        assert context.get("skip_llm") is True
        assert "Local model missing" in str(context.get("llm_output", ""))


def test_controller_escalation_denied_when_provider_key_missing(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="code help")
        context = result["context"]

        assert context.get("escalation_status") == "denied"
        assert context.get("escalation_code") == "provider_key_missing"
        assert isinstance(context.get("escalation_reason"), str)
        assert context.get("skip_llm") is True
        assert "Local model missing" in str(context.get("llm_output", ""))


def test_controller_escalation_denied_when_budget_zero(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 0.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="code help")
        context = result["context"]

        assert context.get("escalation_status") == "denied"
        assert context.get("escalation_code") == "budget_not_allocated"
        assert isinstance(context.get("escalation_reason"), str)
        assert context.get("skip_llm") is True
        assert "Local model missing" in str(context.get("llm_output", ""))


def test_controller_escalation_allowed_uses_registry_provider_and_redacts_prompt(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    provider = StubEscalationProvider(ok=True, output="escalated-response")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "openai", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="contact me at test@example.com")
        context = result["context"]

        assert context.get("escalation_status") == "escalated"
        assert context.get("escalation_redaction_applied") is True
        assert context.get("llm_output") == "escalated-response"
        assert context.get("skip_llm") is False
        assert "test@example.com" not in provider.last_prompt
        assert "[EMAIL_REDACTED]" in provider.last_prompt


def test_controller_escalation_allowed_uses_registered_anthropic_provider(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "anthropic"
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")

    provider = StubEscalationProvider(ok=True, output="anthropic-escalated-response")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "anthropic", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="contact me at test@example.com")
        context = result["context"]

        assert context.get("escalation_status") == "escalated"
        assert context.get("llm_output") == "anthropic-escalated-response"
        assert context.get("skip_llm") is False
        assert "test@example.com" not in provider.last_prompt
        assert "[EMAIL_REDACTED]" in provider.last_prompt


def test_controller_escalation_allowed_provider_failure_sets_failed(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    provider = StubEscalationProvider(ok=False, output="", error="provider failure")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "openai", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=MissingModelPathRegistry(),
        )

        result = service.run(user_input="trigger missing path")
        context = result["context"]

        assert context.get("escalation_status") == "failed"
        assert context.get("escalation_error") == "provider failure"
        assert "Local model missing" in str(context.get("llm_output", ""))


def test_controller_ollama_success_skips_cloud_escalation_path(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = True
        OLLAMA_MODEL = "llama3.2"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    class _OllamaProvider:
        def execute(self, prompt: str, max_tokens: int, seed: int | None):
            _ = prompt
            _ = max_tokens
            _ = seed
            return True, "ollama-response", ""

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(controller_service_module, "OllamaEscalationProvider", _OllamaProvider)

    def _unexpected_cloud_policy_call(*args, **kwargs):
        _ = args
        _ = kwargs
        raise AssertionError("cloud escalation path should not execute after ollama success")

    monkeypatch.setattr(controller_service_module, "decide_escalation", _unexpected_cloud_policy_call)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")
        context = result["context"]

        assert context.get("escalation_status") == "escalated"
        assert context.get("escalation_provider_used") == "ollama"
        assert context.get("llm_output") == "ollama-response"


def test_controller_ollama_failure_falls_through_to_cloud_escalation(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = True
        OLLAMA_MODEL = "llama3.2"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    class _OllamaProvider:
        def execute(self, prompt: str, max_tokens: int, seed: int | None):
            _ = prompt
            _ = max_tokens
            _ = seed
            return False, "", "ollama_unreachable"

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(controller_service_module, "OllamaEscalationProvider", _OllamaProvider)

    def _allow_cloud_policy(request):
        _ = request
        return True, {"code": "ok", "reason": "allowed"}

    monkeypatch.setattr(controller_service_module, "decide_escalation", _allow_cloud_policy)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    provider = StubEscalationProvider(ok=True, output="cloud-response")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "openai", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")
        context = result["context"]

        assert context.get("ollama_fallback_reason") == "ollama_unreachable"
        assert context.get("escalation_status") == "escalated"
        assert context.get("llm_output") == "cloud-response"


def test_controller_ollama_disabled_falls_through_to_cloud_escalation(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_MODEL = "llama3.2"
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    class _UnexpectedOllamaProvider:
        def execute(self, prompt: str, max_tokens: int, seed: int | None):
            _ = prompt
            _ = max_tokens
            _ = seed
            raise AssertionError("ollama should not run when disabled")

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(controller_service_module, "OllamaEscalationProvider", _UnexpectedOllamaProvider)

    def _allow_cloud_policy(request):
        _ = request
        return True, {"code": "ok", "reason": "allowed"}

    monkeypatch.setattr(controller_service_module, "decide_escalation", _allow_cloud_policy)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    provider = StubEscalationProvider(ok=True, output="cloud-response-disabled")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "openai", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")
        context = result["context"]

        assert context.get("escalation_status") == "escalated"
        assert context.get("llm_output") == "cloud-response-disabled"


def test_controller_ollama_enabled_with_blank_model_falls_through_to_cloud(monkeypatch) -> None:
    class _Settings:
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = True
        OLLAMA_MODEL = "   "
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 10.0

    class _UnexpectedOllamaProvider:
        def execute(self, prompt: str, max_tokens: int, seed: int | None):
            _ = prompt
            _ = max_tokens
            _ = seed
            raise AssertionError("ollama should not run when model is blank")

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(controller_service_module, "OllamaEscalationProvider", _UnexpectedOllamaProvider)

    def _allow_cloud_policy(request):
        _ = request
        return True, {"code": "ok", "reason": "allowed"}

    monkeypatch.setattr(controller_service_module, "decide_escalation", _allow_cloud_policy)

    provider = StubEscalationProvider(ok=True, output="cloud-response-blank-model")
    monkeypatch.setitem(controller_service_module._ESCALATION_PROVIDER_REGISTRY, "openai", provider)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")
        context = result["context"]

        assert context.get("escalation_status") == "escalated"
        assert context.get("llm_output") == "cloud-response-blank-model"
        assert context.get("escalation_provider_used") != "ollama"


def test_controller_service_run_uses_dag_executor_path(monkeypatch) -> None:
    original = DAGExecutor.resolve_execution_order
    calls = {"count": 0}

    def _wrapped(self, graph, node_registry):
        calls["count"] += 1
        return original(self, graph, node_registry)

    monkeypatch.setattr(DAGExecutor, "resolve_execution_order", _wrapped)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")

        assert calls["count"] == 1
        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "llm_worker",
            "validator",
        ]
        assert context["workflow_graph"]["entry"] == "router"

        task_state = service.memory.get_task_state(result["task_id"])
        assert isinstance(task_state, dict)
        assert task_state.get("workflow_graph", {}).get("entry") == "router"


def test_controller_service_run_planned_mode_aggregates_subtask_outputs() -> None:
    class StubPlanningLLMModelRegistry(StubModelRegistry):
        def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
            return {"id": "stub-model", "path": "models/stub.gguf"}

        def ensure_model_present(self, model: dict) -> str:
            _ = model
            return "models/stub.gguf"

    class StubPlanningLLMWorker:
        def execute(self, context: dict) -> dict:
            user_input = str(context.get("user_input", ""))
            context["llm_output"] = f"answer::{user_input}"
            context["llm_stream_chunks"] = [context["llm_output"]]
            return context

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubPlanningLLMModelRegistry(),
        )
        service.registry = StubPlanningLLMModelRegistry()
        service_llm_worker_original = service.run

        from backend.workflow.nodes.llm_worker_node import LLMWorkerNode

        original_execute = LLMWorkerNode.execute
        LLMWorkerNode.execute = StubPlanningLLMWorker().execute  # type: ignore[method-assign]
        try:
            result = service.run(
                user_input=(
                    "This is a long prompt designed to trigger planning and produce multiple segments; "
                    "collect requirements; then draft approach; next provide verification."
                )
            )
        finally:
            LLMWorkerNode.execute = original_execute  # type: ignore[method-assign]
            _ = service_llm_worker_original

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("planning_mode") == "planned"
        assert context.get("planning_subtasks") == [
            "This is a long prompt designed to trigger planning and produce multiple segments",
            "collect requirements",
            "draft approach",
        ]
        assert context.get("planning_aggregated_parts") == 3
        assert context.get("planning_subtask_failures") == []
        llm_output = str(context.get("llm_output", ""))
        assert "[Part 1]" in llm_output
        assert "answer::This is a long prompt designed to trigger planning and produce multiple segments" in llm_output
        assert "[Part 2]" in llm_output
        assert "answer::collect requirements" in llm_output
        assert "[Part 3]" in llm_output
        assert "answer::draft approach" in llm_output

        with sqlite3.connect(service.memory.episodic.db_path) as conn:
            subtask_rows = conn.execute(
                """
                SELECT status, content
                FROM decisions
                WHERE task_id = ? AND action_type = 'dag_subtask_event'
                ORDER BY id ASC
                """,
                (result["task_id"],),
            ).fetchall()

            dag_rows = conn.execute(
                """
                SELECT status, content
                FROM decisions
                WHERE task_id = ? AND action_type = 'dag_node_event'
                ORDER BY id ASC
                """,
                (result["task_id"],),
            ).fetchall()

        assert len(subtask_rows) == 3
        for idx, (status, content) in enumerate(subtask_rows, start=1):
            payload = json.loads(content)
            assert status == payload["status"]
            assert payload["subtask_index"] == idx
            assert payload["subtask_count"] == 3
            assert isinstance(payload["subtask_input_preview"], str)
            assert isinstance(payload["subtask_output_preview"], str)
            assert isinstance(payload["subtask_output_empty"], bool)

        # Workflow telemetry surface remains tied to dag_node_event shape only.
        assert dag_rows
        dag_payload = json.loads(dag_rows[0][1])
        assert "event_type" in dag_payload
        assert "subtask_index" not in dag_payload


def test_controller_service_planned_mode_records_empty_subtask_failure_and_still_validates(monkeypatch) -> None:
    class StubPlanningLLMModelRegistry(StubModelRegistry):
        def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
            _ = profile
            _ = hardware
            _ = role
            return {"id": "stub-model", "path": "models/stub.gguf"}

        def ensure_model_present(self, model: dict) -> str:
            _ = model
            return "models/stub.gguf"

    def _stub_constrained_plan(user_input: str, intent: str | None = "") -> dict:
        _ = user_input
        _ = intent
        return {
            "mode": "planned",
            "subtasks": ["first step", "second step"],
            "max_subtasks": 3,
        }

    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode

    def _stub_llm_execute(self, context: dict) -> dict:
        _ = self
        subtask_input = str(context.get("user_input", ""))
        if subtask_input == "first step":
            context["llm_output"] = ""
            context["llm_stream_chunks"] = [""]
        else:
            context["llm_output"] = "This is a sufficiently long assistant response for validator pass."
            context["llm_stream_chunks"] = [context["llm_output"]]
        return context

    monkeypatch.setattr(controller_service_module, "build_constrained_plan", _stub_constrained_plan)
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubPlanningLLMModelRegistry(),
        )

        result = service.run(user_input="planned test input")

    assert result["final_state"] == "ARCHIVE"
    context = result["context"]
    assert context.get("planning_mode") == "planned"

    failures = context.get("planning_subtask_failures")
    assert isinstance(failures, list)
    assert len(failures) == 1
    failure = failures[0]
    assert failure.get("subtask_index") == 1
    assert failure.get("subtask_input_preview") == "first step"
    assert failure.get("reason") == "empty_output"

    # Terminal validation still executes after subtask failure.
    assert context.get("validation_status") == "passed"
    assert context.get("is_valid") is True


def test_controller_service_upload_planned_mode_collapses_redundant_subtask_outputs(monkeypatch) -> None:
    class StubPlanningLLMModelRegistry(StubModelRegistry):
        def select_model(self, profile: str, hardware: str, role: str) -> dict | None:
            _ = profile
            _ = hardware
            _ = role
            return {"id": "stub-model", "path": "models/stub.gguf"}

        def ensure_model_present(self, model: dict) -> str:
            _ = model
            return "models/stub.gguf"

    def _stub_constrained_plan(user_input: str, intent: str | None = "") -> dict:
        _ = user_input
        _ = intent
        return {
            "mode": "planned",
            "subtasks": [
                "extract file purpose",
                "extract file purpose",
                "extract file purpose",
            ],
            "max_subtasks": 3,
        }

    from backend.workflow.nodes.llm_worker_node import LLMWorkerNode

    def _stub_llm_execute(self, context: dict) -> dict:
        _ = self
        _ = context
        output = "The file is an ISO image creation script for Windows ADK."
        context["llm_output"] = output
        context["llm_stream_chunks"] = [output]
        return context

    monkeypatch.setattr(controller_service_module, "build_constrained_plan", _stub_constrained_plan)
    monkeypatch.setattr(LLMWorkerNode, "execute", _stub_llm_execute)

    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubPlanningLLMModelRegistry(),
        )

        result = service.run(
            user_input=(
                "what is this file?\n\n"
                "[ATTACHMENT_CONTEXT_BEGIN]\n"
                "filename=oscdimg.txt\n"
                "set FLDLOC=\"E:/_WORK/OS/W11\"\n"
                "[ATTACHMENT_CONTEXT_END]"
            )
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("planning_mode") == "planned"
        assert context.get("planning_aggregated_parts") == 1

        llm_output = str(context.get("llm_output", ""))
        assert "[Part 1]" not in llm_output
        assert "[Part 2]" not in llm_output
        assert "[Part 3]" not in llm_output
        assert llm_output == "The file is an ISO image creation script for Windows ADK."


def test_controller_service_run_linear_mode_preserved_for_short_prompt() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="short prompt")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("planning_mode") == "linear"
        assert context.get("planning_subtasks") == ["short prompt"]
        assert context.get("planning_max_subtasks") == 3
        assert context.get("planning_subtask_failures") == []
        assert "planning_aggregated_parts" not in context

        with sqlite3.connect(service.memory.episodic.db_path) as conn:
            subtask_rows = conn.execute(
                """
                SELECT status, content
                FROM decisions
                WHERE task_id = ? AND action_type = 'dag_subtask_event'
                ORDER BY id ASC
                """,
                (result["task_id"],),
            ).fetchall()

        assert subtask_rows == []


def test_controller_service_fail_closed_on_validator_quality_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello")

        assert result["final_state"] == "FAILED"
        context = result["context"]
        assert context.get("is_valid") is False
        assert context.get("validation_status") == "failed"
        assert context.get("validation_errors") == [
            "model_error_output",
            "explicit_llm_error",
        ]
        assert result.get("error") == "validation_failed"


def test_controller_service_run_records_dag_node_trace_events() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="trace test")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}

        with sqlite3.connect(service.memory.episodic.db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, content
                FROM decisions
                WHERE task_id = ? AND action_type = 'dag_node_event'
                ORDER BY id ASC
                """,
                (result["task_id"],),
            ).fetchall()

        assert rows, "expected dag_node_event entries"

        parsed = [json.loads(content) for _, content in rows]
        event_types = [row["event_type"] for row in parsed]

        assert "node_start" in event_types
        assert "node_end" in event_types
        assert any(
            row["node_id"] == "router" and row["event_type"] == "node_start"
            for row in parsed
        )
        assert any(
            row["node_id"] == "router" and row["event_type"] == "node_end"
            for row in parsed
        )


def test_controller_service_run_executes_tool_call_node_and_records_trace() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)
        (root / "alpha.txt").write_text("alpha", encoding="utf-8")

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(
            user_input="list files",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "tool_call",
            "llm_worker",
            "validator",
        ]
        assert context["tool_ok"] is True
        assert context["tool_result"]["code"] == "ok"
        assert context["tool_result"]["entries"] == ["alpha.txt"]

        with sqlite3.connect(service.memory.episodic.db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, content
                FROM decisions
                WHERE task_id = ? AND action_type = 'dag_node_event'
                ORDER BY id ASC
                """,
                (result["task_id"],),
            ).fetchall()

        parsed = [json.loads(content) for _, content in rows]
        assert any(
            row["node_id"] == "tool_call" and row["event_type"] == "node_start"
            for row in parsed
        )
        assert any(
            row["node_id"] == "tool_call" and row["event_type"] == "node_end"
            for row in parsed
        )


def test_controller_service_auto_injects_research_tool_call_path() -> None:
    from backend.workflow.nodes.search_web_node import SearchWebNode

    original_execute = SearchWebNode.execute

    def _stub_execute(self, context: dict):
        context["search_results"] = []
        context["search_provider"] = None
        context["search_ok"] = True
        context["search_error"] = None
        return context

    SearchWebNode.execute = _stub_execute  # type: ignore[method-assign]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        try:
            result = service.run(user_input="research latest python packaging guidance")
        finally:
            SearchWebNode.execute = original_execute  # type: ignore[method-assign]

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "research"
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "search_web",
            "llm_worker",
            "validator",
        ]
        assert "tool_name" not in context
        assert context.get("search_ok") is True


def test_controller_research_routes_to_search_web_node() -> None:
    from backend.workflow.nodes.search_web_node import SearchWebNode

    original_execute = SearchWebNode.execute

    def _stub_execute(self, context: dict):
        context["search_results"] = []
        context["search_provider"] = None
        context["search_ok"] = True
        context["search_error"] = None
        return context

    SearchWebNode.execute = _stub_execute  # type: ignore[method-assign]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        try:
            result = service.run(user_input="research latest python packaging guidance")
        finally:
            SearchWebNode.execute = original_execute  # type: ignore[method-assign]

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "research"
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "search_web",
            "llm_worker",
            "validator",
        ]
        assert "tool_name" not in context


def test_controller_service_does_not_inject_tool_call_for_chat_intent() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello there")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "chat"
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "llm_worker",
            "validator",
        ]
        assert "search_web" not in context["workflow_execution_order"]
        assert "tool_name" not in context


def test_controller_chat_does_not_include_search_web_node() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="hello there")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "chat"
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "llm_worker",
            "validator",
        ]
        assert "search_web" not in context["workflow_execution_order"]
        assert "tool_name" not in context


def test_controller_service_preserves_code_intent_graph_without_search_web() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="test code")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "code"
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "llm_worker",
            "validator",
        ]
        assert "search_web" not in context["workflow_execution_order"]
        assert "tool_name" not in context


def test_controller_planning_intent_short_input_forces_planned_mode() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="Please plan my week")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "planning"
        assert context.get("planning_mode") == "planned"
        assert context.get("planning_subtasks") == ["Please plan my week"]


def test_controller_writing_intent_short_input_stays_linear_mode() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(user_input="Write a short email")

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "writing"
        assert context.get("planning_mode") == "linear"
        assert context.get("planning_subtask_failures") == []


def test_controller_service_research_does_not_overwrite_explicit_tool_call() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)
        (root / "alpha.txt").write_text("alpha", encoding="utf-8")

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(
            user_input="research local files",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "research"
        assert context.get("tool_name") == "list_directory"
        assert context.get("tool_ok") is True
        assert context.get("tool_result", {}).get("entries") == ["alpha.txt"]
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "tool_call",
            "llm_worker",
            "validator",
        ]
        assert "search_web" not in context["workflow_execution_order"]


def test_controller_explicit_tool_call_still_uses_tool_call_node() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)
        (root / "alpha.txt").write_text("alpha", encoding="utf-8")

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(
            user_input="research local files",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context.get("intent") == "research"
        assert context.get("tool_name") == "list_directory"
        assert context.get("tool_ok") is True
        assert context.get("tool_result", {}).get("entries") == ["alpha.txt"]
        assert context["workflow_execution_order"] == [
            "router",
            "context_builder",
            "tool_call",
            "llm_worker",
            "validator",
        ]
        assert "search_web" not in context["workflow_execution_order"]


def test_controller_service_research_same_input_same_graph_deterministic() -> None:
    from backend.workflow.nodes.search_web_node import SearchWebNode

    original_execute = SearchWebNode.execute

    def _stub_execute(self, context: dict):
        context["search_results"] = []
        context["search_provider"] = None
        context["search_ok"] = True
        context["search_error"] = None
        return context

    SearchWebNode.execute = _stub_execute  # type: ignore[method-assign]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        try:
            result_a = service.run(user_input="research deterministic graph")
            result_b = service.run(user_input="research deterministic graph")
        finally:
            SearchWebNode.execute = original_execute  # type: ignore[method-assign]

        context_a = result_a["context"]
        context_b = result_b["context"]
        assert context_a["workflow_execution_order"] == context_b["workflow_execution_order"]
        assert context_a["workflow_graph"] == context_b["workflow_graph"]


def test_controller_service_run_tool_call_write_safe_denied_by_default() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        target = root / "blocked.txt"
        result = service.run(
            user_input="attempt write",
            tool_call={
                "tool_name": "write_file",
                "payload": {
                    "path": str(target),
                    "content": "blocked",
                    "encoding": "utf-8",
                },
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        context = result["context"]
        assert context["tool_ok"] is False
        assert context["tool_result"]["code"] == "permission_denied"
        assert not target.exists()


def test_tool_call_node_uses_custom_audit_log_path_and_whitespace_falls_back(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        custom_log_path = Path(tmp_dir) / "custom_security_audit.jsonl"
        fallback_log_path = Path(tmp_dir) / "fallback_security_audit.jsonl"

        def _patched_default_logger() -> SecurityAuditLogger:
            return SecurityAuditLogger(fallback_log_path)

        monkeypatch.setattr(audit_logger_module, "create_default_audit_logger", _patched_default_logger)

        custom_result = service.run(
            user_input="external deny custom",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
                "external_call": True,
                "allow_external": False,
                "external_provider": "provider-custom",
                "external_endpoint": "/custom",
                "audit_log_path": str(custom_log_path),
            },
        )
        assert custom_result["context"]["tool_result"]["code"] == "permission_denied"
        assert custom_log_path.exists()
        custom_events = [json.loads(line) for line in custom_log_path.read_text(encoding="utf-8").splitlines()]
        assert any(event["event_type"] == "permission_denied" for event in custom_events)

        fallback_result = service.run(
            user_input="external deny fallback",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
                "external_call": True,
                "allow_external": False,
                "external_provider": "provider-fallback",
                "external_endpoint": "/fallback",
                "audit_log_path": "   ",
            },
        )
        assert fallback_result["context"]["tool_result"]["code"] == "permission_denied"
        assert fallback_log_path.exists()
        fallback_events = [json.loads(line) for line in fallback_log_path.read_text(encoding="utf-8").splitlines()]
        assert any(event["event_type"] == "permission_denied" for event in fallback_events)


def test_tool_call_node_default_audit_logger_behavior_unchanged_without_override(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        patched_default_path = Path(tmp_dir) / "security_audit.jsonl"

        def _patched_default_logger() -> SecurityAuditLogger:
            return SecurityAuditLogger(patched_default_path)

        monkeypatch.setattr(audit_logger_module, "create_default_audit_logger", _patched_default_logger)

        result = service.run(
            user_input="external deny default",
            tool_call={
                "tool_name": "list_directory",
                "payload": {"path": str(root)},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
                "external_call": True,
                "allow_external": False,
                "external_provider": "provider-default",
                "external_endpoint": "/default",
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        assert result["context"]["tool_ok"] is False
        assert result["context"]["tool_result"]["code"] == "permission_denied"
        assert patched_default_path.exists()
        events = [json.loads(line) for line in patched_default_path.read_text(encoding="utf-8").splitlines()]
        assert any(event["event_type"] == "permission_denied" for event in events)


def test_tool_call_node_attaches_redacted_output_and_logs_pii_events_to_override_path() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        root = Path(tmp_dir) / "tool-root"
        root.mkdir(parents=True, exist_ok=True)
        target = root / "secret.txt"
        target.write_text("contact me at test@example.com", encoding="utf-8")
        audit_log_path = Path(tmp_dir) / "tool_audit.jsonl"

        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubModelRegistry(),
        )

        result = service.run(
            user_input="read file",
            tool_call={
                "tool_name": "read_file",
                "payload": {"path": str(target), "encoding": "utf-8"},
                "allow_write_safe": False,
                "sandbox_roots": [str(root)],
                "external_call": False,
                "redaction_mode": "strict",
                "audit_log_path": str(audit_log_path),
            },
        )

        assert result["final_state"] in {"ARCHIVE", "FAILED"}
        tool_result = result["context"]["tool_result"]
        assert result["context"]["tool_ok"] is True
        assert tool_result["code"] == "ok"
        assert tool_result["content"] == "contact me at test@example.com"
        assert "privacy" in tool_result
        assert "redacted_result_text" in tool_result
        assert tool_result["privacy"]["pii_detected"] is True
        assert tool_result["privacy"]["pii_redacted"] is True
        assert "[EMAIL_REDACTED]" in tool_result["redacted_result_text"]

        assert audit_log_path.exists()
        events = [json.loads(line) for line in audit_log_path.read_text(encoding="utf-8").splitlines()]
        event_types = {event["event_type"] for event in events}
        assert "pii_detected" in event_types
        assert "pii_redacted" in event_types


def test_controller_query_redaction_enabled_redacts_model_bound_prompt_message_path(monkeypatch) -> None:
    class _Settings:
        REDACT_PII_QUERIES = True
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_MODEL = ""
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 0.0

    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "This is a sufficiently long assistant response."}]}

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        raw_input = "Email me at test@example.com"
        result = service.run(user_input=raw_input)

    prompt = str(captured.get("prompt", ""))
    assert "User: Email me at test@example.com" not in prompt
    assert "[EMAIL_REDACTED]" in prompt
    assert result["context"].get("user_input") == raw_input
    assert result["context"].get("redact_pii_queries") is True


def test_controller_query_redaction_disabled_preserves_model_bound_prompt_message_path(monkeypatch) -> None:
    class _Settings:
        REDACT_PII_QUERIES = False
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_MODEL = ""
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 0.0

    captured: dict[str, object] = {}

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": "This is a sufficiently long assistant response."}]}

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        raw_input = "Email me at test@example.com"
        result = service.run(user_input=raw_input)

    prompt = str(captured.get("prompt", ""))
    assert "User: Email me at test@example.com" in prompt
    assert "[EMAIL_REDACTED]" not in prompt
    assert result["context"].get("user_input") == raw_input
    assert result["context"].get("redact_pii_queries") is False


def test_controller_combined_query_and_result_redaction_path_redacts_prompt_persistence_and_semantic_write(
    monkeypatch,
) -> None:
    class _Settings:
        REDACT_PII_QUERIES = True
        REDACT_PII_RESULTS = True
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_MODEL = ""
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 0.0

    captured: dict[str, object] = {}
    pii_output = "Reach me at test@example.com for a status update on the task outcome."

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(self, **kwargs):
            captured.update(kwargs)
            return {"choices": [{"text": pii_output}]}

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        memory = build_recording_memory(tmp_dir)
        service = ControllerService(
            memory_manager=memory,
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        raw_input = "My email is test@example.com"
        result = service.run(user_input=raw_input)

        assert result["final_state"] == "ARCHIVE"

        prompt = str(captured.get("prompt", ""))
        assert "User: My email is test@example.com" not in prompt
        assert "[EMAIL_REDACTED]" in prompt

        task_state = memory.get_task_state(result["task_id"])
        assert isinstance(task_state, dict)
        messages = task_state.get("messages", [])
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        assert assistant_messages
        persisted_assistant = str(assistant_messages[-1].get("content", ""))
        assert "test@example.com" not in persisted_assistant
        assert "[EMAIL_REDACTED]" in persisted_assistant

        assert len(memory.semantic_writes) == 1
        semantic_text = str(memory.semantic_writes[0].get("text", ""))
        assert "test@example.com" not in semantic_text
        assert "[EMAIL_REDACTED]" in semantic_text


def test_controller_wires_retrieval_settings_into_context_builder_retrieval_config(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Settings:
        REDACT_PII_QUERIES = False
        REDACT_PII_RESULTS = False
        MODEL_PATH = "models/"
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_MODEL = ""
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 0.0
        RETRIEVAL_MAX_RESULTS = 17
        RETRIEVAL_MIN_SCORE = 0.4
        RETRIEVAL_TIME_DECAY_TAU_HOURS = 36.0

    class _ContextBuilderStub:
        def __init__(self, *args, **kwargs) -> None:
            _ = args
            captured["retrieval_config"] = kwargs.get("retrieval_config")

        def execute(self, context: dict) -> dict:
            return context

    class _LLMWorkerStub:
        def execute(self, context: dict) -> dict:
            context["llm_output"] = "This output is long enough for validation success."
            context["llm_stream_chunks"] = [context["llm_output"]]
            return context

    class _ValidatorStub:
        def execute(self, context: dict) -> dict:
            context["is_valid"] = True
            context["validation_status"] = "passed"
            context["validation_errors"] = []
            return context

    monkeypatch.setattr(controller_service_module, "Settings", lambda: _Settings)
    monkeypatch.setattr(controller_service_module, "ContextBuilderNode", _ContextBuilderStub)
    monkeypatch.setattr(controller_service_module, "LLMWorkerNode", _LLMWorkerStub)
    monkeypatch.setattr(controller_service_module, "ValidatorNode", _ValidatorStub)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=PresentModelRegistry(),
        )

        result = service.run(user_input="hello")

    assert result["final_state"] == "ARCHIVE"
    retrieval_config = captured.get("retrieval_config")
    assert retrieval_config is not None
    assert getattr(retrieval_config, "max_results") == 17
    assert getattr(retrieval_config, "min_final_score_threshold") == 0.4
    assert getattr(retrieval_config, "time_decay_tau_hours") == 36.0


def test_controller_transcribe_uses_stt_model_selection_and_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.voice.stt_provider.FasterWhisperSTTProvider.transcribe_file",
        lambda self, audio_path: f"transcript::{audio_path}",
    )

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubSTTModelRegistry(),
        )

        result = service.transcribe("tests/fixtures/sample.wav")

    assert result["transcript"] == "transcript::tests/fixtures/sample.wav"
    assert result["model_id"] == "whisper-base"
    assert result["profile"] == "light"
    assert result["hardware"] == "CPU_ONLY"


def test_controller_speak_uses_tts_model_selection_and_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.voice.tts_provider.PiperTTSProvider.synthesize_to_file",
        lambda self, text, output_path: f"{output_path}::{text}",
    )

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        monkeypatch.setenv("DATA_PATH", str(Path(tmp_dir)))
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubTTSModelRegistry(),
        )

        result = service.speak("hello tts")

    assert result["audio_path"].endswith("::hello tts")
    assert result["model_id"] == "piper-tts"
    assert result["profile"] == "light"
    assert result["hardware"] == "CPU_ONLY"


def test_controller_speak_fail_closed_when_tts_config_missing(monkeypatch) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        monkeypatch.setenv("DATA_PATH", str(Path(tmp_dir)))
        service = ControllerService(
            memory_manager=build_memory(tmp_dir),
            hardware_service=StubHardwareService(),
            model_registry=StubTTSMissingConfigRegistry(),
        )

        try:
            service.speak("hello tts")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert str(exc) == "tts_config_not_available"
