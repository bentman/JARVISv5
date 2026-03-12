from datetime import datetime, timezone

from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.search.policy import SearchPolicyRequest, decide_external_search


def _ledger(tmp_path):
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    return SearchBudgetLedger(path=tmp_path / "budget.json", now_provider=lambda: fixed_now)


def test_policy_denies_when_allow_external_false(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=5.0, per_call_estimate_usd=1.0)
    request = SearchPolicyRequest(
        allow_external=False,
        provider_is_external=True,
        provider_is_paid=False,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["reason"] == "external search not allowed"
    assert result["path"] == "blocked"
    assert result["provider_is_external"] is True
    assert result["provider_is_paid"] is False
    assert result["estimated_cost_usd"] == 1.0


def test_policy_allows_free_external_when_within_budget(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.5, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=False,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is True
    assert result["code"] == "ok"
    assert result["reason"] == "allowed"
    assert result["path"] == "free"
    assert result["remaining_budget_usd"] == 1.5
    assert result["estimated_cost_usd"] == 0.5


def test_policy_denies_free_external_when_budget_exceeded(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.8, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=False,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert result["reason"] == "daily budget exceeded"
    assert result["path"] == "blocked"
    assert result["estimated_cost_usd"] == 0.5


def test_policy_denies_paid_external_when_paid_disabled(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=5.0, per_call_estimate_usd=0.5)
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=True,
        allow_paid_search=False,
        paid_key_configured=True,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["reason"] == "paid search not allowed"
    assert result["path"] == "blocked"


def test_policy_denies_paid_external_when_key_missing(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=5.0, per_call_estimate_usd=0.5)
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=True,
        allow_paid_search=True,
        paid_key_configured=False,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "provider_unavailable"
    assert result["reason"] == "paid provider key not configured"
    assert result["path"] == "blocked"


def test_policy_allows_paid_external_when_enabled_key_present_and_budget_ok(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.5, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=True,
        allow_paid_search=True,
        paid_key_configured=True,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is True
    assert result["code"] == "ok"
    assert result["reason"] == "allowed"
    assert result["path"] == "paid"
    assert result["remaining_budget_usd"] == 1.5


def test_policy_denies_paid_external_when_budget_exceeded_even_if_enabled(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.8, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=True,
        allow_paid_search=True,
        paid_key_configured=True,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert result["reason"] == "daily budget exceeded"
    assert result["path"] == "blocked"


def test_policy_allows_non_external_provider_without_external_permission(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.5)
    request = SearchPolicyRequest(
        allow_external=False,
        provider_is_external=False,
        provider_is_paid=False,
        date_key="2026-03-01",
    )

    ok, result = decide_external_search(request, ledger, config)

    assert ok is True
    assert result["code"] == "ok"
    assert result["reason"] == "allowed"
    assert result["path"] == "free"


def test_policy_same_input_same_result_deterministic(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.5)
    request = SearchPolicyRequest(
        allow_external=True,
        provider_is_external=True,
        provider_is_paid=True,
        allow_paid_search=True,
        paid_key_configured=True,
        date_key="2026-03-01",
    )

    ok_1, result_1 = decide_external_search(request, ledger, config)
    ok_2, result_2 = decide_external_search(request, ledger, config)

    assert ok_1 is True
    assert ok_2 is True
    assert result_1 == result_2
