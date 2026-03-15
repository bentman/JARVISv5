import json
import sqlite3
import tempfile
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


def build_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
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
    with tempfile.TemporaryDirectory() as tmp_dir:
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

    with tempfile.TemporaryDirectory() as tmp_dir:
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
        llm_output = str(context.get("llm_output", ""))
        assert "[Part 1]" in llm_output
        assert "answer::This is a long prompt designed to trigger planning and produce multiple segments" in llm_output
        assert "[Part 2]" in llm_output
        assert "answer::collect requirements" in llm_output
        assert "[Part 3]" in llm_output
        assert "answer::draft approach" in llm_output


def test_controller_service_run_linear_mode_preserved_for_short_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
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
        assert "planning_aggregated_parts" not in context


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
