from fastapi.testclient import TestClient
import os

from backend.api.main import app


client = TestClient(app)


def test_settings_endpoint_returns_schema_aligned_keys() -> None:
    response = client.get("/settings")
    assert response.status_code == 200

    body = response.json()
    assert set(
        [
            "app_name",
            "debug",
            "hardware_profile",
            "log_level",
            "model_path",
            "data_path",
            "backend_port",
            "redact_pii_queries",
            "redact_pii_results",
            "allow_external_search",
            "default_search_provider",
            "cache_enabled",
        ]
    ).issubset(body.keys())


def test_settings_endpoint_respects_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "JARVISv5-Test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BACKEND_PORT", "9001")
    monkeypatch.setenv("DEBUG", "false")

    class _EnvSettings:
        APP_NAME = os.environ["APP_NAME"]
        DEBUG = os.environ["DEBUG"].strip().lower() in {"1", "true", "yes", "on", "dev", "debug", "development"}
        HARDWARE_PROFILE = "Medium"
        LOG_LEVEL = os.environ["LOG_LEVEL"]
        MODEL_PATH = "models/"
        DATA_PATH = "data/"
        BACKEND_PORT = int(os.environ["BACKEND_PORT"])

    monkeypatch.setattr("backend.api.main.Settings", lambda: _EnvSettings)

    response = client.get("/settings")
    assert response.status_code == 200

    body = response.json()
    assert body["app_name"] == "JARVISv5-Test"
    assert body["log_level"] == "DEBUG"
    assert body["backend_port"] == 9001
    assert body["debug"] is False


def test_settings_endpoint_invalid_debug_returns_500(monkeypatch) -> None:
    def _raise_settings() -> object:
        raise ValueError("invalid settings")

    monkeypatch.setattr("backend.api.main.Settings", _raise_settings)

    response = client.get("/settings")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "settings_unavailable"
