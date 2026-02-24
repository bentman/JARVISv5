"""
Privacy wrapper for external-call gating and payload preparation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from backend.security.audit_logger import (
    SecurityAuditLogger,
    SecurityEvent,
    SecurityEventType,
)
from backend.security.redactor import PIIRedactor


@dataclass(frozen=True)
class ExternalCallRequest:
    provider: str
    endpoint: str
    payload: dict[str, Any]
    task_id: str | None = None
    allow_external: bool = False
    redaction_mode: Literal["partial", "strict"] = "strict"


class PrivacyExternalCallWrapper:
    """Evaluate policy and prepare a redacted external-call payload."""

    def __init__(self, redactor: PIIRedactor, audit_logger: SecurityAuditLogger) -> None:
        self.redactor = redactor
        self.audit_logger = audit_logger

    @staticmethod
    def _stringify(data: dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

    def _audit_detection_and_redaction(
        self,
        *,
        pii_detected: bool,
        pii_redacted: bool,
        summary: dict[str, Any],
        mode: Literal["partial", "strict"],
        task_id: str | None,
        phase: str,
        tool_name: str,
    ) -> None:
        summary_text = self._stringify(
            {
                "tool_name": tool_name,
                "phase": phase,
                "mode": mode,
                "summary": summary,
            }
        )
        if pii_detected:
            self.audit_logger.log_pii_detection(
                pii_types=list(summary.get("types", [])),
                context=summary_text,
                task_id=task_id,
            )
        if pii_redacted:
            self.audit_logger.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.PII_REDACTED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    context={
                        "tool_name": tool_name,
                        "phase": phase,
                        "mode": mode,
                        "summary": summary,
                    },
                    severity="warning",
                    task_id=task_id,
                )
            )

    def scan_tool_input(
        self,
        *,
        tool_name: str,
        payload: dict[str, Any],
        redaction_mode: Literal["partial", "strict"],
        task_id: str | None = None,
    ) -> dict[str, Any]:
        payload_text = self._stringify(payload)
        redaction = self.redactor.redact(payload_text, mode=redaction_mode)
        pii_redacted = redaction.redacted != payload_text
        self._audit_detection_and_redaction(
            pii_detected=redaction.pii_detected,
            pii_redacted=pii_redacted,
            summary=redaction.summary,
            mode=redaction_mode,
            task_id=task_id,
            phase="input",
            tool_name=tool_name,
        )
        return {
            "payload_text": redaction.redacted,
            "pii_detected": redaction.pii_detected,
            "pii_redacted": pii_redacted,
            "summary": redaction.summary,
            "mode": redaction_mode,
        }

    def scan_tool_output(
        self,
        *,
        tool_name: str,
        result: dict[str, Any],
        redaction_mode: Literal["partial", "strict"],
        task_id: str | None = None,
    ) -> dict[str, Any]:
        result_text = self._stringify(result)
        redaction = self.redactor.redact(result_text, mode=redaction_mode)
        pii_redacted = redaction.redacted != result_text
        self._audit_detection_and_redaction(
            pii_detected=redaction.pii_detected,
            pii_redacted=pii_redacted,
            summary=redaction.summary,
            mode=redaction_mode,
            task_id=task_id,
            phase="output",
            tool_name=tool_name,
        )
        return {
            "result_text": redaction.redacted,
            "pii_detected": redaction.pii_detected,
            "pii_redacted": pii_redacted,
            "summary": redaction.summary,
            "mode": redaction_mode,
        }

    def evaluate_and_prepare_external_call(
        self,
        request: ExternalCallRequest,
    ) -> tuple[bool, dict[str, Any]]:
        provider = request.provider
        endpoint = request.endpoint

        if not request.allow_external:
            self.audit_logger.log_permission_denied(
                operation=f"external_call:{provider}:{endpoint}",
                reason="allow_external_false",
                task_id=request.task_id,
            )
            return False, {
                "code": "permission_denied",
                "message": "External call blocked by policy",
                "policy_decision": "blocked",
                "provider": provider,
                "endpoint": endpoint,
                "task_id": request.task_id,
            }

        payload_text = json.dumps(
            request.payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )

        try:
            redaction_result = self.redactor.redact(payload_text, mode=request.redaction_mode)
        except ValueError:
            self.audit_logger.log_permission_denied(
                operation=f"external_call:{provider}:{endpoint}",
                reason=f"invalid_redaction_mode:{request.redaction_mode}",
                task_id=request.task_id,
            )
            return False, {
                "code": "validation_error",
                "message": "Invalid redaction mode",
                "policy_decision": "blocked",
                "provider": provider,
                "endpoint": endpoint,
                "task_id": request.task_id,
            }

        if redaction_result.pii_detected:
            pii_types = redaction_result.summary["types"]
            pii_counts = redaction_result.summary["counts"]
            self.audit_logger.log_pii_detection(
                pii_types=pii_types,
                context=(
                    f"provider={provider};endpoint={endpoint};"
                    f"pii_counts={json.dumps(pii_counts, sort_keys=True, ensure_ascii=True)}"
                ),
                task_id=request.task_id,
            )

        redacted_payload = {
            "payload_text": redaction_result.redacted,
            "redaction_mode": request.redaction_mode,
            "pii_detected": redaction_result.pii_detected,
            "pii_summary": redaction_result.summary,
        }
        self.audit_logger.log_external_call(
            provider=provider,
            endpoint=endpoint,
            redacted_payload=redacted_payload,
            task_id=request.task_id,
        )

        return True, {
            "code": "external_call_prepared",
            "message": "External call prepared",
            "policy_decision": "allowed",
            "provider": provider,
            "endpoint": endpoint,
            "task_id": request.task_id,
            "redaction_mode": request.redaction_mode,
            "redacted_payload_text": redaction_result.redacted,
            "pii_detected": redaction_result.pii_detected,
            "pii_summary": redaction_result.summary,
        }


def create_default_privacy_wrapper(log_path: str | None = None) -> PrivacyExternalCallWrapper:
    """Create a privacy wrapper with default security components."""
    audit_path = "data/logs/security_audit.jsonl" if log_path is None else log_path
    return PrivacyExternalCallWrapper(
        redactor=PIIRedactor(),
        audit_logger=SecurityAuditLogger(audit_path),
    )
