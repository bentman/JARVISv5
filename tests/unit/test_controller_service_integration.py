import json
import sqlite3
import tempfile
from pathlib import Path

import backend.security.audit_logger as audit_logger_module
from backend.controller.controller_service import ControllerService
from backend.security.audit_logger import SecurityAuditLogger
from backend.workflow.dag_executor import DAGExecutor
from backend.memory.memory_manager import MemoryManager
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
