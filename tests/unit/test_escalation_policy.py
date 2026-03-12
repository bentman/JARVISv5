from typing import Any

from backend.models.escalation_policy import (
    EscalationPolicyRequest,
    EscalationTrigger,
    StubEscalationProvider,
    decide_escalation,
)


def _base_request(**overrides: Any) -> EscalationPolicyRequest:
    payload: dict[str, Any] = {
        "trigger": EscalationTrigger.LOCAL_MODEL_MISSING,
        "allow_escalation": True,
        "provider": "openai",
        "budget_usd": 5.0,
        "estimated_cost_usd": 1.0,
    }
    payload.update(overrides)
    return EscalationPolicyRequest(**payload)


def test_policy_denies_when_escalation_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(
        _base_request(allow_escalation=False)
    )

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["path"] == "blocked"


def test_policy_denies_when_provider_not_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(
        _base_request(provider="   ")
    )

    assert ok is False
    assert result["code"] == "provider_not_configured"
    assert result["path"] == "blocked"


def test_policy_denies_when_provider_unsupported(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(
        _base_request(provider="unsupported")
    )

    assert ok is False
    assert result["code"] == "provider_unsupported"
    assert result["provider_supported"] is False
    assert result["path"] == "blocked"


def test_policy_denies_when_provider_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    ok, result = decide_escalation(_base_request(provider="openai"))

    assert ok is False
    assert result["code"] == "provider_key_missing"
    assert result["provider_supported"] is True
    assert result["provider_configured"] is False
    assert result["provider_key_configured"] is False
    assert result["path"] == "blocked"


def test_policy_denies_when_budget_not_allocated(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(
        _base_request(budget_usd=0.0)
    )

    assert ok is False
    assert result["code"] == "budget_not_allocated"
    assert result["path"] == "blocked"


def test_policy_denies_when_cost_exceeds_budget(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(
        _base_request(budget_usd=1.0, estimated_cost_usd=1.5)
    )

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert result["path"] == "blocked"


def test_policy_allows_when_all_gates_pass(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    ok, result = decide_escalation(_base_request())

    assert ok is True
    assert result["code"] == "ok"
    assert result["path"] == "escalated"
    assert result["provider"] == "openai"
    assert result["provider_supported"] is True
    assert result["provider_configured"] is True
    assert result["provider_key_configured"] is True


def test_policy_is_deterministic_for_same_input(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")
    request = _base_request()

    ok_a, result_a = decide_escalation(request)
    ok_b, result_b = decide_escalation(request)

    assert ok_a is True
    assert ok_b is True
    assert result_a == result_b


def test_stub_provider_returns_deterministic_output() -> None:
    provider = StubEscalationProvider()

    result_a = provider.execute("prompt", max_tokens=128, seed=7)
    result_b = provider.execute("prompt", max_tokens=128, seed=7)

    assert result_a == (True, "stub_escalation_output", "")
    assert result_b == (True, "stub_escalation_output", "")
