"""
PII redaction engine for M5.1.

Implements roadmap API shape with v4 regex/token parity for detection + redaction.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


class PIIType(str, Enum):
    """Types of PII supported by the v5 redactor."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IBAN = "iban"
    IP_ADDRESS = "ip_address"
    BANK_ACCOUNT = "bank_account"


@dataclass(frozen=True)
class PIIMatch:
    """A detected PII span."""

    pii_type: PIIType
    start: int
    end: int
    original_text: str


@dataclass(frozen=True)
class RedactionResult:
    """Result of redaction operation."""

    original: str
    redacted: str
    matches: list[PIIMatch]
    pii_detected: bool
    summary: dict[str, Any]


class PIIRedactor:
    """Detect and redact PII from text."""

    def __init__(self) -> None:
        # Order is deterministic and mirrors v4 behavior needs.
        self.patterns: tuple[tuple[PIIType, re.Pattern[str]], ...] = (
            (PIIType.EMAIL, re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
            (PIIType.PHONE, re.compile(r"(?<!\d)\d{3}-\d{3}-\d{4}(?!\d)")),
            (PIIType.PHONE, re.compile(r"(?<!\d)\(\d{3}\)\s\d{3}-\d{4}(?!\d)")),
            (PIIType.PHONE, re.compile(r"(?<!\d)\d{3}-\d{4}(?!\d)")),
            (PIIType.SSN, re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
            (PIIType.CREDIT_CARD, re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
            (PIIType.IBAN, re.compile(r"\b[A-Z]{2}[0-9A-Z]{2}[0-9A-Z]{1,30}\b")),
            (PIIType.IP_ADDRESS, re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
            (PIIType.BANK_ACCOUNT, re.compile(r"\b\d{9,19}\b")),
        )

    def detect(self, text: str) -> list[PIIMatch]:
        """Detect PII in text without redacting."""
        matches: list[PIIMatch] = []

        for pii_type, pattern in self.patterns:
            for match in pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        start=match.start(),
                        end=match.end(),
                        original_text=match.group(),
                    )
                )

        return sorted(matches, key=lambda m: (m.start, m.end, m.pii_type.value, m.original_text))

    def redact(self, text: str, mode: Literal["partial", "strict"] = "partial") -> RedactionResult:
        """Detect and redact PII from text using v4 parity modes."""
        if mode not in ("partial", "strict"):
            raise ValueError("mode must be 'partial' or 'strict'")

        matches = self.detect(text)
        if not matches:
            return RedactionResult(
                original=text,
                redacted=text,
                matches=[],
                pii_detected=False,
                summary={"types": [], "counts": {}, "total": 0},
            )

        replacement_by_type = {
            PIIType.EMAIL: "[EMAIL_REDACTED]",
            PIIType.PHONE: "[PHONE_REDACTED]",
            PIIType.SSN: "[SSN_REDACTED]",
            PIIType.CREDIT_CARD: "[CREDIT_CARD_REDACTED]",
            PIIType.IBAN: "[IBAN_REDACTED]",
            PIIType.IP_ADDRESS: "[IP_REDACTED]",
        }

        redactable_partial = {PIIType.EMAIL, PIIType.PHONE}
        redactable_strict = {
            PIIType.EMAIL,
            PIIType.PHONE,
            PIIType.SSN,
            PIIType.CREDIT_CARD,
            PIIType.IBAN,
            PIIType.IP_ADDRESS,
        }
        redactable = redactable_strict if mode == "strict" else redactable_partial

        redacted = text
        for match in reversed(matches):
            if match.pii_type not in redactable:
                continue
            replacement = replacement_by_type[match.pii_type]
            redacted = redacted[: match.start] + replacement + redacted[match.end :]

        counts: dict[str, int] = {}
        for match in matches:
            key = match.pii_type.value
            counts[key] = counts.get(key, 0) + 1

        sorted_types = sorted(counts.keys())
        sorted_counts = {key: counts[key] for key in sorted_types}

        return RedactionResult(
            original=text,
            redacted=redacted,
            matches=matches,
            pii_detected=True,
            summary={
                "types": sorted_types,
                "counts": sorted_counts,
                "total": len(matches),
            },
        )


def create_default_redactor() -> PIIRedactor:
    """Create redactor with default configuration."""
    return PIIRedactor()
