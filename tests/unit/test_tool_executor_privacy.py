from pathlib import Path

from pydantic import BaseModel

from backend.security.audit_logger import SecurityAuditLogger, SecurityEventType
from backend.security.privacy_wrapper import PrivacyExternalCallWrapper
from backend.security.redactor import PIIRedactor
from backend.tools.executor import ToolExecutionRequest, execute_tool_call
from backend.tools.registry import PermissionTier, ToolDefinition, ToolRegistry
from backend.tools.sandbox import Sandbox, SandboxConfig


class ExternalInput(BaseModel):
    text: str


def _build_registry_and_sandbox(root: Path) -> tuple[ToolRegistry, Sandbox]:
    sandbox = Sandbox(SandboxConfig(allowed_roots=(root,)))
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="external_tool",
            description="External tool stub",
            permission_tier=PermissionTier.READ_ONLY,
            input_model=ExternalInput,
        )
    )
    return registry, sandbox


def _build_privacy_wrapper(tmp_path: Path) -> PrivacyExternalCallWrapper:
    logger = SecurityAuditLogger(tmp_path / "security_audit.jsonl")
    return PrivacyExternalCallWrapper(redactor=PIIRedactor(), audit_logger=logger)


def test_external_blocked_by_default_and_audited(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    wrapper = _build_privacy_wrapper(tmp_path)

    called = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        called["count"] += 1
        return True, {"code": "ok"}

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "hello"},
            external_call=True,
            allow_external=False,
            external_provider="provider-x",
            external_endpoint="/v1/test",
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": _handler},
        privacy_wrapper=wrapper,
    )

    assert ok is False
    assert result["code"] == "permission_denied"
    assert called["count"] == 0

    events = wrapper.audit_logger.read_events(event_type=SecurityEventType.PERMISSION_DENIED)
    assert len(events) == 1
    assert "provider-x" in events[0].context["operation"]
    assert "/v1/test" in events[0].context["operation"]


def test_external_allowed_logs_external_and_pii_and_executes_handler(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    wrapper = _build_privacy_wrapper(tmp_path)

    called = {"count": 0}

    def _handler(_sandbox: Sandbox, payload: dict) -> tuple[bool, dict]:
        called["count"] += 1
        return True, {"code": "ok", "echo": payload["text"]}

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "email test@example.com"},
            external_call=True,
            allow_external=True,
            external_provider="provider-y",
            external_endpoint="/v1/send",
            redaction_mode="strict",
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": _handler},
        privacy_wrapper=wrapper,
    )

    assert ok is True
    assert result["code"] == "ok"
    assert called["count"] == 1
    assert "privacy" in result
    assert "redacted_result_text" in result

    external_events = wrapper.audit_logger.read_events(event_type=SecurityEventType.EXTERNAL_CALL_INITIATED)
    pii_events = wrapper.audit_logger.read_events(event_type=SecurityEventType.PII_DETECTED)
    assert len(external_events) == 1
    assert len(pii_events) >= 1


def test_non_external_call_path_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "plain"},
            external_call=False,
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": lambda _s, payload: (True, {"code": "ok", "echo": payload["text"]})},
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["echo"] == "plain"


def test_non_external_input_with_pii_detected_but_payload_unmodified_for_handler(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    wrapper = _build_privacy_wrapper(tmp_path)
    captured: dict[str, str] = {}

    def _handler(_sandbox: Sandbox, payload: dict) -> tuple[bool, dict]:
        captured["text"] = payload["text"]
        return True, {"code": "ok"}

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "email test@example.com"},
            external_call=False,
            redaction_mode="strict",
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": _handler},
        privacy_wrapper=wrapper,
    )

    assert ok is True
    assert captured["text"] == "email test@example.com"
    assert result["code"] == "ok"
    pii_events = wrapper.audit_logger.read_events(event_type=SecurityEventType.PII_DETECTED)
    assert len(pii_events) >= 1


def test_output_pii_attaches_redacted_result_and_logs_pii_redacted(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    wrapper = _build_privacy_wrapper(tmp_path)

    def _handler(_sandbox: Sandbox, payload: dict) -> tuple[bool, dict]:
        return True, {"code": "ok", "result": f"contact {payload['text']}"}

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "test@example.com"},
            external_call=False,
            redaction_mode="strict",
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": _handler},
        privacy_wrapper=wrapper,
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["result"] == "contact test@example.com"
    assert "redacted_result_text" in result
    assert "[EMAIL_REDACTED]" in result["redacted_result_text"]
    assert result["privacy"]["pii_detected"] is True
    assert result["privacy"]["pii_redacted"] is True

    redacted_events = wrapper.audit_logger.read_events(event_type=SecurityEventType.PII_REDACTED)
    assert len(redacted_events) >= 1


def test_no_pii_keeps_behavior_and_logs_no_pii_redacted(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)
    wrapper = _build_privacy_wrapper(tmp_path)

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "plain text"},
            external_call=False,
            redaction_mode="strict",
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": lambda _s, payload: (True, {"code": "ok", "echo": payload["text"]})},
        privacy_wrapper=wrapper,
    )

    assert ok is True
    assert result["code"] == "ok"
    assert result["echo"] == "plain text"
    assert result["privacy"]["pii_detected"] is False
    assert result["privacy"]["pii_redacted"] is False
    redacted_events = wrapper.audit_logger.read_events(event_type=SecurityEventType.PII_REDACTED)
    assert len(redacted_events) == 0


def test_external_call_requires_explicit_privacy_wrapper(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    registry, sandbox = _build_registry_and_sandbox(root)

    called = {"count": 0}

    def _handler(_sandbox: Sandbox, _payload: dict) -> tuple[bool, dict]:
        called["count"] += 1
        return True, {"code": "ok"}

    ok, result = execute_tool_call(
        request=ToolExecutionRequest(
            tool_name="external_tool",
            payload={"text": "hello"},
            external_call=True,
            allow_external=True,
        ),
        registry=registry,
        sandbox=sandbox,
        dispatch_map={"external_tool": _handler},
        privacy_wrapper=None,
    )

    assert ok is False
    assert result["code"] == "configuration_error"
    assert result["message"] == "privacy_wrapper is required for external_call"
    assert called["count"] == 0
