from datetime import datetime, timezone

from backend.search.budget import SearchBudgetConfig, SearchBudgetLedger
from backend.search.policy import SearchPolicyRequest, decide_external_search


def _ledger(tmp_path):
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    return SearchBudgetLedger(path=tmp_path / "budget.json", now_provider=lambda: fixed_now)


def test_policy_denies_when_allow_external_false(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=5.0, per_call_estimate_usd=1.0)
    request = SearchPolicyRequest(allow_external=False, date_key="2026-03-01")

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "permission_denied"
    assert result["reason"] == "external search not allowed"
    assert result["estimated_cost_usd"] == 1.0


def test_policy_allows_when_explicit_and_within_budget(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=2.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.5, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(allow_external=True, date_key="2026-03-01")

    ok, result = decide_external_search(request, ledger, config)

    assert ok is True
    assert result["code"] == "ok"
    assert result["reason"] == "allowed"
    assert result["remaining_budget_usd"] == 1.5
    assert result["estimated_cost_usd"] == 0.5


def test_policy_denies_when_explicit_but_budget_exceeded(tmp_path) -> None:
    ledger = _ledger(tmp_path)
    config = SearchBudgetConfig(daily_limit_usd=1.0, per_call_estimate_usd=0.5)
    ledger.record_spend(0.8, date_key="2026-03-01", provider="test")
    request = SearchPolicyRequest(allow_external=True, date_key="2026-03-01")

    ok, result = decide_external_search(request, ledger, config)

    assert ok is False
    assert result["code"] == "budget_exceeded"
    assert result["reason"] == "daily budget exceeded"
    assert result["estimated_cost_usd"] == 0.5
