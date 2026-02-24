import json
from pathlib import Path

from backend.security.audit_logger import SecurityAuditLogger, SecurityEventType
from backend.security.privacy_wrapper import ExternalCallRequest, PrivacyExternalCallWrapper
from backend.security.redactor import PIIRedactor


def _make_wrapper(tmp_path: Path) -> tuple[PrivacyExternalCallWrapper, SecurityAuditLogger]:
    logger = SecurityAuditLogger(tmp_path / "security_audit.jsonl")
    wrapper = PrivacyExternalCallWrapper(redactor=PIIRedactor(), audit_logger=logger)
    return wrapper, logger


def test_deny_by_default_blocks_and_logs_permission_denied(tmp_path: Path) -> None:
    wrapper, logger = _make_wrapper(tmp_path)
    request = ExternalCallRequest(
        provider="OpenAI",
        endpoint="/v1/chat/completions",
        payload={"prompt": "hello"},
        task_id="task-001",
        allow_external=False,
    )

    ok, result = wrapper.evaluate_and_prepare_external_call(request)

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["policy_decision"] == "blocked"

    events = logger.read_events()
    assert len(events) == 1
    assert events[0].event_type == SecurityEventType.PERMISSION_DENIED
    assert "OpenAI" in events[0].context["operation"]
    assert "/v1/chat/completions" in events[0].context["operation"]


def test_allow_path_redacts_payload_and_logs_external_call(tmp_path: Path) -> None:
    wrapper, logger = _make_wrapper(tmp_path)
    request = ExternalCallRequest(
        provider="OpenAI",
        endpoint="/v1/chat/completions",
        payload={"prompt": "Email me at test@example.com"},
        task_id="task-002",
        allow_external=True,
        redaction_mode="strict",
    )

    ok, result = wrapper.evaluate_and_prepare_external_call(request)

    assert ok is True
    assert result["code"] == "external_call_prepared"
    assert result["policy_decision"] == "allowed"
    assert "[EMAIL_REDACTED]" in result["redacted_payload_text"]
    assert "test@example.com" not in result["redacted_payload_text"]

    events = logger.read_events(event_type=SecurityEventType.EXTERNAL_CALL_INITIATED)
    assert len(events) == 1
    assert events[0].context["provider"] == "OpenAI"
    assert events[0].context["endpoint"] == "/v1/chat/completions"
    assert "payload_text" in events[0].context["payload"]
    assert "test@example.com" not in events[0].context["payload"]["payload_text"]


def test_allow_path_emits_pii_detected_event_with_counts(tmp_path: Path) -> None:
    wrapper, logger = _make_wrapper(tmp_path)
    request = ExternalCallRequest(
        provider="ProviderX",
        endpoint="/endpoint",
        payload={"a": "x@example.com", "b": "555-123-4567"},
        task_id="task-003",
        allow_external=True,
    )

    ok, _ = wrapper.evaluate_and_prepare_external_call(request)

    assert ok is True
    pii_events = logger.read_events(event_type=SecurityEventType.PII_DETECTED)
    assert len(pii_events) == 1
    assert "email" in pii_events[0].context["pii_types"]
    assert "phone" in pii_events[0].context["pii_types"]
    assert "pii_counts=" in pii_events[0].context["context_snippet"]


def test_redaction_mode_partial_vs_strict_changes_output(tmp_path: Path) -> None:
    wrapper, _ = _make_wrapper(tmp_path)
    payload = {"text": "Email test@example.com Card 1234-5678-9012-3456"}

    ok_partial, partial = wrapper.evaluate_and_prepare_external_call(
        ExternalCallRequest(
            provider="OpenAI",
            endpoint="/v1/chat/completions",
            payload=payload,
            allow_external=True,
            redaction_mode="partial",
        )
    )
    ok_strict, strict = wrapper.evaluate_and_prepare_external_call(
        ExternalCallRequest(
            provider="OpenAI",
            endpoint="/v1/chat/completions",
            payload=payload,
            allow_external=True,
            redaction_mode="strict",
        )
    )

    assert ok_partial is True
    assert ok_strict is True
    assert "[EMAIL_REDACTED]" in partial["redacted_payload_text"]
    assert "[EMAIL_REDACTED]" in strict["redacted_payload_text"]
    assert "1234-5678-9012-3456" in partial["redacted_payload_text"]
    assert "[CREDIT_CARD_REDACTED]" in strict["redacted_payload_text"]


def test_audit_log_lines_are_jsonl_with_expected_event_types(tmp_path: Path) -> None:
    wrapper, logger = _make_wrapper(tmp_path)

    allow_request = ExternalCallRequest(
        provider="ProviderA",
        endpoint="/ok",
        payload={"text": "contact x@example.com"},
        allow_external=True,
    )
    deny_request = ExternalCallRequest(
        provider="ProviderB",
        endpoint="/deny",
        payload={"text": "hello"},
        allow_external=False,
    )

    wrapper.evaluate_and_prepare_external_call(allow_request)
    wrapper.evaluate_and_prepare_external_call(deny_request)

    lines = logger.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 3
    events = [json.loads(line) for line in lines]
    event_types = {event["event_type"] for event in events}
    assert "external_call_initiated" in event_types
    assert "permission_denied" in event_types
    assert "pii_detected" in event_types


def test_invalid_redaction_mode_fails_closed_and_audits_denial(tmp_path: Path) -> None:
    wrapper, logger = _make_wrapper(tmp_path)
    request = ExternalCallRequest(
        provider="OpenAI",
        endpoint="/v1/chat/completions",
        payload={"prompt": "hello"},
        allow_external=True,
        redaction_mode="strict",  # type-safe placeholder
    )

    # Inject invalid mode for runtime fail-closed validation path.
    object.__setattr__(request, "redaction_mode", "invalid")

    ok, result = wrapper.evaluate_and_prepare_external_call(request)

    assert ok is False
    assert result["code"] == "validation_error"
    assert result["policy_decision"] == "blocked"

    events = logger.read_events(event_type=SecurityEventType.PERMISSION_DENIED)
    assert len(events) == 1
    assert "invalid_redaction_mode" in events[0].context["reason"]
