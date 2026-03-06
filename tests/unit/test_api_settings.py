from fastapi.testclient import TestClient
import os
from pathlib import Path

from backend.api.main import app


client = TestClient(app)


def _write_env(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _read_env(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_settings_endpoint_returns_schema_aligned_keys(monkeypatch) -> None:
    class _DefaultSettings:
        APP_NAME = "JARVISv5"
        DEBUG = True
        HARDWARE_PROFILE = "Medium"
        LOG_LEVEL = "INFO"
        MODEL_PATH = "models/"
        DATA_PATH = "data/"
        BACKEND_PORT = 8000
        REDACT_PII_QUERIES = True
        REDACT_PII_RESULTS = False
        ALLOW_EXTERNAL_SEARCH = False
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        CACHE_ENABLED = False

    monkeypatch.setattr("backend.api.main.Settings", lambda: _DefaultSettings)

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
    assert body["redact_pii_queries"] is True
    assert body["redact_pii_results"] is False
    assert body["allow_external_search"] is False
    assert body["default_search_provider"] == "duckduckgo"
    assert body["cache_enabled"] is False


def test_settings_endpoint_respects_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "JARVISv5-Test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BACKEND_PORT", "9001")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("REDACT_PII_QUERIES", "false")
    monkeypatch.setenv("REDACT_PII_RESULTS", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_SEARCH", "true")
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", "tavily")
    monkeypatch.setenv("CACHE_ENABLED", "true")

    class _EnvSettings:
        APP_NAME = os.environ["APP_NAME"]
        DEBUG = os.environ["DEBUG"].strip().lower() in {"1", "true", "yes", "on", "dev", "debug", "development"}
        HARDWARE_PROFILE = "Medium"
        LOG_LEVEL = os.environ["LOG_LEVEL"]
        MODEL_PATH = "models/"
        DATA_PATH = "data/"
        BACKEND_PORT = int(os.environ["BACKEND_PORT"])
        REDACT_PII_QUERIES = os.environ["REDACT_PII_QUERIES"].strip().lower() in {"1", "true", "yes", "on"}
        REDACT_PII_RESULTS = os.environ["REDACT_PII_RESULTS"].strip().lower() in {"1", "true", "yes", "on"}
        ALLOW_EXTERNAL_SEARCH = os.environ["ALLOW_EXTERNAL_SEARCH"].strip().lower() in {"1", "true", "yes", "on"}
        DEFAULT_SEARCH_PROVIDER = os.environ["DEFAULT_SEARCH_PROVIDER"]
        CACHE_ENABLED = os.environ["CACHE_ENABLED"].strip().lower() in {"1", "true", "yes", "on"}

    monkeypatch.setattr("backend.api.main.Settings", lambda: _EnvSettings)

    response = client.get("/settings")
    assert response.status_code == 200

    body = response.json()
    assert body["app_name"] == "JARVISv5-Test"
    assert body["log_level"] == "DEBUG"
    assert body["backend_port"] == 9001
    assert body["debug"] is False
    assert body["redact_pii_queries"] is False
    assert body["redact_pii_results"] is True
    assert body["allow_external_search"] is True
    assert body["default_search_provider"] == "tavily"
    assert body["cache_enabled"] is True


def test_settings_endpoint_invalid_debug_returns_500(monkeypatch) -> None:
    def _raise_settings() -> object:
        raise ValueError("invalid settings")

    monkeypatch.setattr("backend.api.main.Settings", _raise_settings)

    response = client.get("/settings")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "settings_unavailable"


def test_settings_write_endpoint_updates_projection_and_returns_restart_headers_for_hardware_profile(
    monkeypatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    _write_env(
        env_path,
        "\n".join(
            [
                "APP_NAME=JARVISv5",
                "DEBUG=true",
                "HARDWARE_PROFILE=medium",
                "LOG_LEVEL=INFO",
                "MODEL_PATH=models/",
                "DATA_PATH=data/",
                "BACKEND_PORT=8000",
                "REDACT_PII_QUERIES=true",
                "REDACT_PII_RESULTS=false",
                "ALLOW_EXTERNAL_SEARCH=false",
                "DEFAULT_SEARCH_PROVIDER=duckduckgo",
                "CACHE_ENABLED=false",
            ]
        )
        + "\n",
    )
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/settings",
        json={
            "hardware_profile": "heavy",
            "log_level": "warning",
            "allow_external_search": True,
            "default_search_provider": "tavily",
            "cache_enabled": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hardware_profile"] == "heavy"
    assert body["log_level"] == "WARNING"
    assert body["allow_external_search"] is True
    assert body["default_search_provider"] == "tavily"
    assert body["cache_enabled"] is True

    assert response.headers.get("X-Settings-Restart-Required") == "true"
    restart_fields_header = response.headers.get("X-Settings-Restart-Required-Fields", "")
    restart_fields = [item for item in restart_fields_header.split(",") if item]
    assert "hardware_profile" in restart_fields

    hot_applied_header = response.headers.get("X-Settings-Hot-Applied-Fields", "")
    hot_applied_fields = [item for item in hot_applied_header.split(",") if item]
    assert "hardware_profile" not in hot_applied_fields
    assert set(hot_applied_fields) == {
        "log_level",
        "allow_external_search",
        "default_search_provider",
        "cache_enabled",
    }


def test_settings_write_endpoint_rejects_invalid_value_without_partial_write(
    monkeypatch, tmp_path: Path
) -> None:
    env_path = tmp_path / ".env"
    original = "\n".join(
        [
            "APP_NAME=JARVISv5",
            "DEBUG=true",
            "HARDWARE_PROFILE=medium",
            "LOG_LEVEL=INFO",
            "ALLOW_EXTERNAL_SEARCH=false",
            "DEFAULT_SEARCH_PROVIDER=duckduckgo",
            "CACHE_ENABLED=false",
        ]
    ) + "\n"
    _write_env(env_path, original)
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/settings",
        json={
            "log_level": "INFO",
            "default_search_provider": "invalid-provider",
        },
    )

    assert response.status_code == 422
    assert _read_env(env_path) == original


def test_settings_write_endpoint_requires_at_least_one_field(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    _write_env(env_path, "APP_NAME=JARVISv5\n")
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post("/settings", json={})
    assert response.status_code == 400
    assert response.json().get("detail") == "no_settings_updates_provided"
