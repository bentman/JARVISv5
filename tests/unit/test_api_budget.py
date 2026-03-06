from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_budget_endpoint_returns_schema_aligned_fields(monkeypatch) -> None:
    monkeypatch.setenv("DAILY_BUDGET_USD", "2.5")
    monkeypatch.setenv("MONTHLY_BUDGET_USD", "10.0")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.today_key", lambda self: "2026-03-01")

    spend_by_day = {
        "2026-03-01": 1.25,
        "2026-02-28": 2.0,
    }

    def _get_spent(self, date_key: str) -> float:
        return float(spend_by_day.get(date_key, 0.0))

    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.get_spent", _get_spent)

    response = client.get("/budget")
    assert response.status_code == 200

    body = response.json()
    assert set(["daily", "monthly"]).issubset(body.keys())
    assert set(["limit_usd", "spent_usd", "remaining_usd"]).issubset(body["daily"].keys())
    assert set(["limit_usd", "spent_usd", "remaining_usd"]).issubset(body["monthly"].keys())
    assert body["daily"]["limit_usd"] == 2.5
    assert body["daily"]["spent_usd"] == 1.25
    assert body["daily"]["remaining_usd"] == 1.25
    assert body["monthly"]["limit_usd"] == 10.0
    assert body["monthly"]["spent_usd"] == 3.25
    assert body["monthly"]["remaining_usd"] == 6.75


def test_budget_endpoint_respects_daily_limit_env_override(monkeypatch) -> None:
    monkeypatch.setenv("DAILY_BUDGET_USD", "9.75")
    monkeypatch.setenv("MONTHLY_BUDGET_USD", "20.0")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.today_key", lambda self: "2026-03-01")

    spend_by_day = {
        "2026-03-01": 0.75,
        "2026-02-28": 0.25,
    }

    def _get_spent(self, date_key: str) -> float:
        return float(spend_by_day.get(date_key, 0.0))

    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.get_spent", _get_spent)

    response = client.get("/budget")
    assert response.status_code == 200

    body = response.json()
    assert body["daily"]["limit_usd"] == 9.75
    assert body["daily"]["spent_usd"] == 0.75
    assert body["daily"]["remaining_usd"] == 9.0
    assert body["monthly"]["limit_usd"] == 20.0
    assert body["monthly"]["spent_usd"] == 1.0
    assert body["monthly"]["remaining_usd"] == 19.0


def test_budget_endpoint_unavailable_returns_500(monkeypatch) -> None:
    def _raise_init(self, *args, **kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.__init__", _raise_init)

    response = client.get("/budget")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "budget_unavailable"
