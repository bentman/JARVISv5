from datetime import datetime, timezone

from backend.search.budget import SearchBudgetLedger


def test_budget_load_save_roundtrip(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    ledger_path = tmp_path / "budget.json"
    ledger = SearchBudgetLedger(path=ledger_path, now_provider=lambda: fixed_now)

    date_key = "2026-03-01"
    ledger.record_spend(1.25, date_key=date_key, provider="test", task_id="task-1")

    reloaded = SearchBudgetLedger(path=ledger_path, now_provider=lambda: fixed_now)
    assert reloaded.get_spent(date_key) == 1.25
    assert reloaded.remaining_budget_usd(date_key, daily_limit_usd=2.0) == 0.75


def test_budget_missing_and_corrupt_file_are_fail_safe(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    missing_path = tmp_path / "missing.json"
    missing = SearchBudgetLedger(path=missing_path, now_provider=lambda: fixed_now)
    assert missing.get_spent("2026-03-01") == 0.0

    corrupt_path = tmp_path / "corrupt.json"
    corrupt_path.write_text("{not-json", encoding="utf-8")
    corrupt = SearchBudgetLedger(path=corrupt_path, now_provider=lambda: fixed_now)
    assert corrupt.get_spent("2026-03-01") == 0.0


def test_budget_accumulation_remaining_and_can_spend_math(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 1, 8, 30, 0, tzinfo=timezone.utc)
    ledger = SearchBudgetLedger(path=tmp_path / "budget.json", now_provider=lambda: fixed_now)
    date_key = ledger.today_key()

    assert date_key == "2026-03-01"
    assert ledger.can_spend(0.5, date_key=date_key, daily_limit_usd=1.0)

    ledger.record_spend(0.6, date_key=date_key, provider="test")
    ledger.record_spend(0.1, date_key=date_key, provider="test")

    assert ledger.get_spent(date_key) == 0.7
    assert ledger.remaining_budget_usd(date_key, daily_limit_usd=1.0) == 0.30000000000000004
    assert ledger.can_spend(0.3, date_key=date_key, daily_limit_usd=1.0)
    assert not ledger.can_spend(0.31, date_key=date_key, daily_limit_usd=1.0)
