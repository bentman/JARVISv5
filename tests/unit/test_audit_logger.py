import json
from datetime import datetime, timezone
from pathlib import Path

from backend.security.audit_logger import (
    SecurityAuditLogger,
    SecurityEvent,
    SecurityEventType,
)


def _make_logger(tmp_path: Path, name: str) -> SecurityAuditLogger:
    return SecurityAuditLogger(tmp_path / name)


def test_jsonl_append_and_read_back(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, "jsonl_append_read_back.jsonl")

    event_one = SecurityEvent(
        event_type=SecurityEventType.PII_DETECTED,
        timestamp="2026-02-24T12:00:00+00:00",
        context={"k": "v1"},
        severity="warning",
        task_id="task-1",
    )
    event_two = SecurityEvent(
        event_type=SecurityEventType.PERMISSION_DENIED,
        timestamp="2026-02-24T12:01:00+00:00",
        context={"k": "v2"},
        severity="warning",
        task_id="task-2",
    )

    logger.log_event(event_one)
    logger.log_event(event_two)

    lines = logger.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event_type"] == "pii_detected"
    assert json.loads(lines[1])["event_type"] == "permission_denied"

    events = logger.read_events()
    assert len(events) == 2
    assert events[0].task_id == "task-1"
    assert events[1].task_id == "task-2"


def test_filter_by_event_type(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, "filter_event_type.jsonl")

    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp="2026-02-24T12:00:00+00:00",
            context={},
            severity="warning",
        )
    )
    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.EXTERNAL_CALL_INITIATED,
            timestamp="2026-02-24T12:01:00+00:00",
            context={},
            severity="info",
        )
    )

    filtered = logger.read_events(event_type=SecurityEventType.EXTERNAL_CALL_INITIATED)
    assert len(filtered) == 1
    assert filtered[0].event_type == SecurityEventType.EXTERNAL_CALL_INITIATED


def test_filter_by_since_with_fixed_timestamps(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, "filter_since_fixed.jsonl")

    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp="2026-02-24T12:00:00+00:00",
            context={"index": 1},
            severity="warning",
        )
    )
    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp="2026-02-24T12:10:00+00:00",
            context={"index": 2},
            severity="warning",
        )
    )

    since = datetime(2026, 2, 24, 12, 5, 0, tzinfo=timezone.utc)
    filtered = logger.read_events(since=since)
    assert len(filtered) == 1
    assert filtered[0].context["index"] == 2


def test_since_treats_naive_timestamps_as_utc_for_backward_tolerance(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, "filter_since_naive_tolerance.jsonl")

    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp="2026-02-24T12:00:00",
            context={"kind": "legacy"},
            severity="warning",
        )
    )
    logger.log_event(
        SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp="2026-02-24T12:10:00+00:00",
            context={"kind": "current"},
            severity="warning",
        )
    )

    since_naive = datetime(2026, 2, 24, 12, 5, 0)
    filtered = logger.read_events(since=since_naive)

    assert len(filtered) == 1
    assert filtered[0].context["kind"] == "current"


def test_convenience_helpers_emit_expected_fields_and_parseable_timestamps(tmp_path: Path) -> None:
    logger = _make_logger(tmp_path, "helpers.jsonl")

    long_context = "x" * 150
    logger.log_pii_detection(["EMAIL", "PHONE"], long_context, task_id="task-123")
    logger.log_external_call("OpenAI", "/v1/chat/completions", {"prompt": "[REDACTED]"}, task_id="task-123")
    logger.log_permission_denied("external_call", "policy_block", task_id="task-123")

    events = logger.read_events()
    assert len(events) == 3

    pii_event = events[0]
    ext_event = events[1]
    deny_event = events[2]

    assert pii_event.event_type == SecurityEventType.PII_DETECTED
    assert pii_event.severity == "warning"
    assert set(pii_event.context.keys()) == {"pii_types", "context_snippet"}
    assert pii_event.context["pii_types"] == ["EMAIL", "PHONE"]
    assert len(pii_event.context["context_snippet"]) == 103
    assert pii_event.context["context_snippet"].endswith("...")

    assert ext_event.event_type == SecurityEventType.EXTERNAL_CALL_INITIATED
    assert ext_event.severity == "info"
    assert set(ext_event.context.keys()) == {"provider", "endpoint", "payload"}
    assert ext_event.context["provider"] == "OpenAI"

    assert deny_event.event_type == SecurityEventType.PERMISSION_DENIED
    assert deny_event.severity == "warning"
    assert set(deny_event.context.keys()) == {"operation", "reason"}
    assert deny_event.context["operation"] == "external_call"

    for event in events:
        parsed = datetime.fromisoformat(event.timestamp)
        assert parsed.tzinfo is not None
