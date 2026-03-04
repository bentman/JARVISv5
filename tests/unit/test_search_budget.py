from datetime import datetime, timezone

import pytest

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


def test_budget_daily_summary_parity_with_existing_daily_math(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 15, 9, 0, 0, tzinfo=timezone.utc)
    ledger = SearchBudgetLedger(path=tmp_path / "budget_daily_summary.json", now_provider=lambda: fixed_now)

    ledger.record_spend(0.4, date_key="2026-03-15", provider="test")
    ledger.record_spend(0.35, date_key="2026-03-15", provider="test")

    daily = ledger.get_daily_summary(daily_limit_usd=1.5)

    assert daily["date_key"] == "2026-03-15"
    assert daily["limit_usd"] == 1.5
    assert daily["spent_usd"] == ledger.get_spent("2026-03-15")
    assert daily["remaining_usd"] == ledger.remaining_budget_usd("2026-03-15", 1.5)


def test_budget_rolling_30d_boundary_and_monthly_summary(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)
    ledger = SearchBudgetLedger(path=tmp_path / "budget_rolling_30d.json", now_provider=lambda: fixed_now)

    # Included in rolling 30-day window ending 2026-03-31 (inclusive)
    ledger.record_spend(1.0, date_key="2026-03-31", provider="test")
    ledger.record_spend(2.0, date_key="2026-03-02", provider="test")
    # Excluded boundary (31 days ago)
    ledger.record_spend(10.0, date_key="2026-03-01", provider="test")

    rolling = ledger.get_rolling_30d_spent(end_date_key="2026-03-31")
    assert rolling == pytest.approx(3.0)

    monthly = ledger.get_monthly_summary(monthly_limit_usd=5.0, end_date_key="2026-03-31")
    assert monthly["window"] == "rolling_30d_utc"
    assert monthly["end_date_key"] == "2026-03-31"
    assert monthly["limit_usd"] == 5.0
    assert monthly["spent_usd"] == pytest.approx(3.0)
    assert monthly["remaining_usd"] == pytest.approx(2.0)


def test_budget_new_summary_helpers_fail_safe_on_missing_and_corrupt(tmp_path) -> None:
    fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    missing = SearchBudgetLedger(path=tmp_path / "missing_helpers.json", now_provider=lambda: fixed_now)
    missing_daily = missing.get_daily_summary(daily_limit_usd=2.0)
    missing_monthly = missing.get_monthly_summary(monthly_limit_usd=10.0)
    assert missing_daily["date_key"] == "2026-03-01"
    assert missing_daily["spent_usd"] == 0.0
    assert missing_daily["remaining_usd"] == 2.0
    assert missing_monthly["window"] == "rolling_30d_utc"
    assert missing_monthly["spent_usd"] == 0.0
    assert missing_monthly["remaining_usd"] == 10.0

    corrupt_path = tmp_path / "corrupt_helpers.json"
    corrupt_path.write_text("{not-json", encoding="utf-8")
    corrupt = SearchBudgetLedger(path=corrupt_path, now_provider=lambda: fixed_now)
    corrupt_daily = corrupt.get_daily_summary(daily_limit_usd=1.25)
    corrupt_rolling = corrupt.get_rolling_30d_spent()
    assert corrupt_daily["spent_usd"] == 0.0
    assert corrupt_daily["remaining_usd"] == 1.25
    assert corrupt_rolling == 0.0
