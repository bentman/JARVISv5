from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_budget_endpoint_returns_schema_aligned_fields(monkeypatch) -> None:
    monkeypatch.setenv("DAILY_BUDGET_USD", "2.5")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.today_key", lambda self: "2026-03-01")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.get_spent", lambda self, _date_key: 1.25)
    monkeypatch.setattr(
        "backend.search.budget.SearchBudgetLedger.remaining_budget_usd",
        lambda self, _date_key, _daily_limit_usd: 1.25,
    )

    response = client.get("/budget")
    assert response.status_code == 200

    body = response.json()
    assert set(["daily", "monthly"]).issubset(body.keys())
    assert set(["limit_usd", "spent_usd", "remaining_usd"]).issubset(body["daily"].keys())
    assert body["daily"]["limit_usd"] == 2.5
    assert body["daily"]["spent_usd"] == 1.25
    assert body["daily"]["remaining_usd"] == 1.25
    assert body["monthly"] is None


def test_budget_endpoint_respects_daily_limit_env_override(monkeypatch) -> None:
    monkeypatch.setenv("DAILY_BUDGET_USD", "9.75")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.today_key", lambda self: "2026-03-01")
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.get_spent", lambda self, _date_key: 0.75)
    monkeypatch.setattr(
        "backend.search.budget.SearchBudgetLedger.remaining_budget_usd",
        lambda self, _date_key, daily_limit_usd: float(daily_limit_usd) - 0.75,
    )

    response = client.get("/budget")
    assert response.status_code == 200

    body = response.json()
    assert body["daily"]["limit_usd"] == 9.75
    assert body["daily"]["spent_usd"] == 0.75
    assert body["daily"]["remaining_usd"] == 9.0


def test_budget_endpoint_unavailable_returns_500(monkeypatch) -> None:
    def _raise_init(self, *args, **kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.__init__", _raise_init)

    response = client.get("/budget")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "budget_unavailable"
