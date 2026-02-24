"""
Security Audit Logger - Record security events for compliance and debugging.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class SecurityEventType(str, Enum):
    """Types of security events."""

    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    EXTERNAL_CALL_INITIATED = "external_call_initiated"
    EXTERNAL_CALL_COMPLETED = "external_call_completed"
    PERMISSION_DENIED = "permission_denied"
    ENCRYPTION_PERFORMED = "encryption_performed"
    DECRYPTION_PERFORMED = "decryption_performed"
    SUSPICIOUS_PATTERN = "suspicious_pattern"


@dataclass
class SecurityEvent:
    """A security event record."""

    event_type: SecurityEventType
    timestamp: str
    context: dict[str, Any]
    severity: str  # "info", "warning", "critical"
    task_id: str | None = None
    user_id: str | None = None


class SecurityAuditLogger:
    """Log security events to file."""

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: SecurityEvent) -> None:
        """Append one security event to the JSONL log file."""
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=True) + "\n")
            handle.flush()

    def log_pii_detection(
        self,
        pii_types: list[str],
        context: str,
        task_id: str | None = None,
    ) -> None:
        """Log PII detection event."""
        event = SecurityEvent(
            event_type=SecurityEventType.PII_DETECTED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={
                "pii_types": pii_types,
                "context_snippet": context[:100] + "..." if len(context) > 100 else context,
            },
            severity="warning",
            task_id=task_id,
        )
        self.log_event(event)

    def log_external_call(
        self,
        provider: str,
        endpoint: str,
        redacted_payload: dict[str, Any],
        task_id: str | None = None,
    ) -> None:
        """Log external API call."""
        event = SecurityEvent(
            event_type=SecurityEventType.EXTERNAL_CALL_INITIATED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={
                "provider": provider,
                "endpoint": endpoint,
                "payload": redacted_payload,
            },
            severity="info",
            task_id=task_id,
        )
        self.log_event(event)

    def log_permission_denied(
        self,
        operation: str,
        reason: str,
        task_id: str | None = None,
    ) -> None:
        """Log permission denial."""
        event = SecurityEvent(
            event_type=SecurityEventType.PERMISSION_DENIED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            context={
                "operation": operation,
                "reason": reason,
            },
            severity="warning",
            task_id=task_id,
        )
        self.log_event(event)

    def read_events(
        self,
        event_type: SecurityEventType | None = None,
        since: datetime | None = None,
    ) -> list[SecurityEvent]:
        """Read events from log file with optional filtering."""
        if not self.log_path.exists():
            return []

        normalized_since = since
        if normalized_since is not None and normalized_since.tzinfo is None:
            normalized_since = normalized_since.replace(tzinfo=timezone.utc)

        events: list[SecurityEvent] = []
        with open(self.log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                event_dict = json.loads(line)
                parsed_type = SecurityEventType(event_dict["event_type"])
                event = SecurityEvent(
                    event_type=parsed_type,
                    timestamp=event_dict["timestamp"],
                    context=event_dict["context"],
                    severity=event_dict["severity"],
                    task_id=event_dict.get("task_id"),
                    user_id=event_dict.get("user_id"),
                )

                if event_type is not None and event.event_type != event_type:
                    continue

                if normalized_since is not None:
                    event_time = datetime.fromisoformat(event.timestamp)
                    if event_time.tzinfo is None:
                        event_time = event_time.replace(tzinfo=timezone.utc)
                    if event_time < normalized_since:
                        continue

                events.append(event)

        return events


def create_default_audit_logger() -> SecurityAuditLogger:
    """Create audit logger with default path."""
    return SecurityAuditLogger("data/logs/security_audit.jsonl")
