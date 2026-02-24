from backend.security.redactor import PIIRedactor, PIIType


def test_redaction_partial_parity_with_v4() -> None:
    redactor = PIIRedactor()
    text = "Contact me at 555-0199 or test@example.com. Card: 1234-5678-9012-3456"

    result = redactor.redact(text, mode="partial")

    assert result.pii_detected is True
    assert "[EMAIL_REDACTED]" in result.redacted
    assert "[PHONE_REDACTED]" in result.redacted
    assert "1234-5678-9012-3456" in result.redacted


def test_redaction_strict_parity_with_v4() -> None:
    redactor = PIIRedactor()
    text = "Contact me at 555-0199 or test@example.com. Card: 1234-5678-9012-3456"

    result = redactor.redact(text, mode="strict")

    assert result.pii_detected is True
    assert "[EMAIL_REDACTED]" in result.redacted
    assert "[PHONE_REDACTED]" in result.redacted
    assert "[CREDIT_CARD_REDACTED]" in result.redacted


def test_detect_covers_all_v4_regex_categories() -> None:
    redactor = PIIRedactor()
    text = (
        "Email alpha@example.com. "
        "Phone1 555-123-4567. "
        "Phone2 (555) 987-6543. "
        "Phone3 555-0199. "
        "SSN 123-45-6789. "
        "Card 1234-5678-9012-3456. "
        "IBAN GB82WEST12345698765432. "
        "IP 192.168.1.10. "
        "Acct 123456789012."
    )

    matches = redactor.detect(text)
    types = {m.pii_type for m in matches}

    assert PIIType.EMAIL in types
    assert PIIType.PHONE in types
    assert PIIType.SSN in types
    assert PIIType.CREDIT_CARD in types
    assert PIIType.IBAN in types
    assert PIIType.IP_ADDRESS in types
    assert PIIType.BANK_ACCOUNT in types


def test_strict_redacts_ssn_iban_and_ip() -> None:
    redactor = PIIRedactor()
    text = "SSN 123-45-6789 IBAN GB82WEST12345698765432 IP 10.2.3.4"

    result = redactor.redact(text, mode="strict")

    assert "[SSN_REDACTED]" in result.redacted
    assert "[IBAN_REDACTED]" in result.redacted
    assert "[IP_REDACTED]" in result.redacted


def test_bank_account_detected_but_not_redacted_in_both_modes() -> None:
    redactor = PIIRedactor()
    text = "Bank account 123456789012 should remain literal."

    partial = redactor.redact(text, mode="partial")
    strict = redactor.redact(text, mode="strict")

    assert any(m.pii_type == PIIType.BANK_ACCOUNT for m in partial.matches)
    assert any(m.pii_type == PIIType.BANK_ACCOUNT for m in strict.matches)
    assert "123456789012" in partial.redacted
    assert "123456789012" in strict.redacted


def test_no_pii_returns_identity_and_empty_summary() -> None:
    redactor = PIIRedactor()
    text = "This sentence contains no sensitive patterns."

    result = redactor.redact(text, mode="partial")

    assert result.pii_detected is False
    assert result.original == text
    assert result.redacted == text
    assert result.matches == []
    assert result.summary == {"types": [], "counts": {}, "total": 0}


def test_summary_is_deterministic_and_sorted() -> None:
    redactor = PIIRedactor()
    text = (
        "z@example.com y@example.com "
        "and 555-0199 plus 123-45-6789 and 10.0.0.1 and 10.0.0.2"
    )

    result = redactor.redact(text, mode="strict")

    assert result.summary["types"] == sorted(result.summary["types"])
    assert list(result.summary["counts"].keys()) == sorted(result.summary["counts"].keys())
    assert result.summary["total"] == len(result.matches)
    assert result.summary["counts"]["email"] == 2
    assert result.summary["counts"]["phone"] == 1
    assert result.summary["counts"]["ssn"] == 1
    assert result.summary["counts"]["ip_address"] == 2


def test_determinism_same_input_same_output_and_summary() -> None:
    redactor = PIIRedactor()
    text = (
        "Email test@example.com "
        "Card 1234-5678-9012-3456 "
        "Phone 555-123-4567 "
        "IP 192.168.10.20 "
        "IBAN GB82WEST12345698765432 "
        "Acct 123456789012"
    )

    first = redactor.redact(text, mode="strict")
    second = redactor.redact(text, mode="strict")

    assert first.redacted == second.redacted
    assert first.matches == second.matches
    assert first.summary == second.summary
