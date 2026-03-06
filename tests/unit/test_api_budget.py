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


def test_budget_update_endpoint_updates_limits_and_returns_projection(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DAILY_BUDGET_USD", raising=False)
    monkeypatch.delenv("MONTHLY_BUDGET_USD", raising=False)
    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.today_key", lambda self: "2026-03-01")
    env_path = tmp_path / ".env"
    env_path.write_text("DAILY_BUDGET_USD=2.5\nMONTHLY_BUDGET_USD=10.0\n", encoding="utf-8")
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    spend_by_day = {
        "2026-03-01": 1.0,
        "2026-02-28": 0.5,
    }

    def _get_spent(self, date_key: str) -> float:
        return float(spend_by_day.get(date_key, 0.0))

    monkeypatch.setattr("backend.search.budget.SearchBudgetLedger.get_spent", _get_spent)

    response = client.post(
        "/budget",
        json={
            "daily_limit_usd": 9.75,
            "monthly_limit_usd": 25.0,
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["daily"]["limit_usd"] == 9.75
    assert body["daily"]["spent_usd"] == 1.0
    assert body["daily"]["remaining_usd"] == 8.75
    assert body["monthly"]["limit_usd"] == 25.0
    assert body["monthly"]["spent_usd"] == 1.5
    assert body["monthly"]["remaining_usd"] == 23.5


def test_budget_update_endpoint_rejects_empty_update(monkeypatch) -> None:
    response = client.post("/budget", json={})
    assert response.status_code == 400
    body = response.json()
    assert body.get("detail") == "no_budget_updates_provided"


def test_budget_update_endpoint_rejects_invalid_values(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", tmp_path / ".env")

    response = client.post(
        "/budget",
        json={
            "daily_limit_usd": -1,
        },
    )
    assert response.status_code == 422


def test_budget_update_endpoint_has_no_partial_write_on_invalid_mixed_update(monkeypatch, tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("DAILY_BUDGET_USD=2.5\nMONTHLY_BUDGET_USD=10.0\n", encoding="utf-8")
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/budget",
        json={
            "daily_limit_usd": 9.75,
            "monthly_limit_usd": -5,
        },
    )
    assert response.status_code == 422

    content = env_path.read_text(encoding="utf-8")
    assert "DAILY_BUDGET_USD=2.5" in content
    assert "MONTHLY_BUDGET_USD=10.0" in content
