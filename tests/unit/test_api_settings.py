from fastapi.testclient import TestClient
import os
from pathlib import Path
import pytest

from backend.api.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _stub_ollama_model_options(monkeypatch):
    monkeypatch.setattr("backend.config.settings.fetch_ollama_model_options", lambda _url: [])


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
        ALLOW_PAID_SEARCH = False
        DEFAULT_SEARCH_PROVIDER = "duckduckgo"
        SEARCH_SEARXNG_URL = "http://searxng:8080/search"
        TAVILY_API_KEY = ""
        CACHE_ENABLED = False
        ALLOW_MODEL_ESCALATION = False
        ESCALATION_PROVIDER = ""
        ESCALATION_BUDGET_USD = 0.0
        ALLOW_OLLAMA_ESCALATION = False
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = ""

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
            "allow_paid_search",
            "default_search_provider",
            "searxng_url",
            "tavily_key_configured",
            "cache_enabled",
            "allow_model_escalation",
            "escalation_provider",
            "escalation_budget_usd",
            "allow_ollama_escalation",
            "ollama_base_url",
            "ollama_model",
            "ollama_model_options",
            "escalation_configured_providers",
        ]
    ).issubset(body.keys())
    assert body["redact_pii_queries"] is True
    assert body["redact_pii_results"] is False
    assert body["allow_external_search"] is False
    assert body["allow_paid_search"] is False
    assert body["default_search_provider"] == "duckduckgo"
    assert body["searxng_url"] == "http://searxng:8080/search"
    assert body["tavily_key_configured"] is False
    assert body["cache_enabled"] is False
    assert body["allow_model_escalation"] is False
    assert body["escalation_provider"] == ""
    assert body["escalation_budget_usd"] == 0.0
    assert body["allow_ollama_escalation"] is False
    assert body["ollama_base_url"] == "http://host.docker.internal:11434"
    assert body["ollama_model"] == ""
    assert body["ollama_model_options"] == []
    assert isinstance(body["escalation_configured_providers"], list)


def test_settings_endpoint_respects_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "JARVISv5-Test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BACKEND_PORT", "9001")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("REDACT_PII_QUERIES", "false")
    monkeypatch.setenv("REDACT_PII_RESULTS", "true")
    monkeypatch.setenv("ALLOW_EXTERNAL_SEARCH", "true")
    monkeypatch.setenv("ALLOW_PAID_SEARCH", "true")
    monkeypatch.setenv("DEFAULT_SEARCH_PROVIDER", "tavily")
    monkeypatch.setenv("SEARCH_SEARXNG_URL", "http://localhost:18080/search")
    monkeypatch.setenv("TAVILY_API_KEY", "demo-key")
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("ALLOW_MODEL_ESCALATION", "true")
    monkeypatch.setenv("ESCALATION_PROVIDER", "openai")
    monkeypatch.setenv("ESCALATION_BUDGET_USD", "3.25")
    monkeypatch.setenv("ALLOW_OLLAMA_ESCALATION", "true")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")

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
        ALLOW_PAID_SEARCH = os.environ["ALLOW_PAID_SEARCH"].strip().lower() in {"1", "true", "yes", "on"}
        DEFAULT_SEARCH_PROVIDER = os.environ["DEFAULT_SEARCH_PROVIDER"]
        SEARCH_SEARXNG_URL = os.environ["SEARCH_SEARXNG_URL"]
        TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
        CACHE_ENABLED = os.environ["CACHE_ENABLED"].strip().lower() in {"1", "true", "yes", "on"}
        ALLOW_MODEL_ESCALATION = os.environ["ALLOW_MODEL_ESCALATION"].strip().lower() in {"1", "true", "yes", "on"}
        ESCALATION_PROVIDER = os.environ["ESCALATION_PROVIDER"]
        ESCALATION_BUDGET_USD = float(os.environ["ESCALATION_BUDGET_USD"])
        ALLOW_OLLAMA_ESCALATION = os.environ["ALLOW_OLLAMA_ESCALATION"].strip().lower() in {"1", "true", "yes", "on"}
        OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]
        OLLAMA_MODEL = os.environ["OLLAMA_MODEL"]

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
    assert body["allow_paid_search"] is True
    assert body["default_search_provider"] == "tavily"
    assert body["searxng_url"] == "http://localhost:18080/search"
    assert body["tavily_key_configured"] is True
    assert body["cache_enabled"] is True
    assert body["allow_model_escalation"] is True
    assert body["escalation_provider"] == "openai"
    assert body["escalation_budget_usd"] == 3.25
    assert body["allow_ollama_escalation"] is True
    assert body["ollama_base_url"] == "http://localhost:11434"
    assert body["ollama_model"] == "llama3.2"
    assert body["ollama_model_options"] == []
    assert isinstance(body["escalation_configured_providers"], list)


def test_settings_endpoint_invalid_debug_returns_500(monkeypatch) -> None:
    def _raise_settings() -> object:
        raise ValueError("invalid settings")

    monkeypatch.setattr("backend.api.main.Settings", _raise_settings)

    response = client.get("/settings")
    assert response.status_code == 500
    body = response.json()
    assert body.get("detail") == "settings_unavailable"


def test_settings_get_explicit_search_projection_fields(monkeypatch) -> None:
    class _Settings:
        APP_NAME = "JARVISv5"
        DEBUG = True
        HARDWARE_PROFILE = "Medium"
        LOG_LEVEL = "INFO"
        MODEL_PATH = "models/"
        DATA_PATH = "data/"
        BACKEND_PORT = 8000
        REDACT_PII_QUERIES = True
        REDACT_PII_RESULTS = False
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = True
        DEFAULT_SEARCH_PROVIDER = "tavily"
        SEARCH_SEARXNG_URL = "http://localhost:18080/search"
        TAVILY_API_KEY = "configured-key"
        CACHE_ENABLED = False
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "anthropic"
        ESCALATION_BUDGET_USD = 7.0
        ALLOW_OLLAMA_ESCALATION = True
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "llama3.2"

    monkeypatch.setattr("backend.api.main.Settings", lambda: _Settings)

    response = client.get("/settings")
    assert response.status_code == 200

    body = response.json()
    assert body["allow_paid_search"] is True
    assert body["searxng_url"] == "http://localhost:18080/search"
    assert body["tavily_key_configured"] is True
    assert body["allow_model_escalation"] is True
    assert body["escalation_provider"] == "anthropic"
    assert body["escalation_budget_usd"] == 7.0
    assert body["allow_ollama_escalation"] is True
    assert body["ollama_base_url"] == "http://host.docker.internal:11434"
    assert body["ollama_model"] == "llama3.2"
    assert body["ollama_model_options"] == []
    assert isinstance(body["escalation_configured_providers"], list)


def test_settings_get_does_not_expose_raw_api_key_fields_or_values(monkeypatch) -> None:
    class _Settings:
        APP_NAME = "JARVISv5"
        DEBUG = True
        HARDWARE_PROFILE = "Medium"
        LOG_LEVEL = "INFO"
        MODEL_PATH = "models/"
        DATA_PATH = "data/"
        BACKEND_PORT = 8000
        REDACT_PII_QUERIES = True
        REDACT_PII_RESULTS = False
        ALLOW_EXTERNAL_SEARCH = True
        ALLOW_PAID_SEARCH = True
        DEFAULT_SEARCH_PROVIDER = "tavily"
        SEARCH_SEARXNG_URL = "http://localhost:18080/search"
        TAVILY_API_KEY = "tavily-secret"
        CACHE_ENABLED = False
        ALLOW_MODEL_ESCALATION = True
        ESCALATION_PROVIDER = "openai"
        ESCALATION_BUDGET_USD = 7.0
        ALLOW_OLLAMA_ESCALATION = True
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "llama3.2"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setenv("GROK_API_KEY", "grok-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setattr("backend.api.main.Settings", lambda: _Settings)

    response = client.get("/settings")
    assert response.status_code == 200

    body = response.json()
    response_text = response.text

    assert "anthropic_api_key" not in body
    assert "gemini_api_key" not in body
    assert "grok_api_key" not in body
    assert "openai_api_key" not in body

    assert "anthropic-secret" not in response_text
    assert "gemini-secret" not in response_text
    assert "grok-secret" not in response_text
    assert "openai-secret" not in response_text
    assert "tavily-secret" not in response_text


def test_settings_write_endpoint_updates_projection_and_returns_restart_headers_for_hardware_profile(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
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
                "ALLOW_PAID_SEARCH=false",
                "DEFAULT_SEARCH_PROVIDER=duckduckgo",
                "SEARCH_SEARXNG_URL=http://searxng:8080/search",
                "TAVILY_API_KEY=",
                "CACHE_ENABLED=false",
                "ALLOW_MODEL_ESCALATION=false",
                "ESCALATION_PROVIDER=",
                "ESCALATION_BUDGET_USD=0.0",
                "ALLOW_OLLAMA_ESCALATION=false",
                "OLLAMA_BASE_URL=http://host.docker.internal:11434",
                "OLLAMA_MODEL=",
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
            "redact_pii_queries": False,
            "redact_pii_results": True,
            "allow_external_search": True,
            "default_search_provider": "tavily",
            "cache_enabled": True,
            "allow_model_escalation": True,
            "escalation_provider": "openai",
            "allow_ollama_escalation": True,
            "ollama_model": "llama3.2",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hardware_profile"] == "heavy"
    assert body["log_level"] == "WARNING"
    assert body["redact_pii_queries"] is False
    assert body["redact_pii_results"] is True
    assert body["allow_external_search"] is True
    assert body["allow_paid_search"] is False
    assert body["default_search_provider"] == "tavily"
    assert body["searxng_url"] == "http://searxng:8080/search"
    assert body["tavily_key_configured"] is False
    assert body["cache_enabled"] is True
    assert body["allow_model_escalation"] is True
    assert body["escalation_provider"] == "openai"
    assert body["escalation_budget_usd"] == 0.0
    assert body["allow_ollama_escalation"] is True
    assert body["ollama_base_url"] == "http://host.docker.internal:11434"
    assert body["ollama_model"] == "llama3.2"
    assert body["ollama_model_options"] == []
    assert isinstance(body["escalation_configured_providers"], list)

    persisted = _read_env(env_path)
    assert "REDACT_PII_QUERIES=false" in persisted
    assert "REDACT_PII_RESULTS=true" in persisted
    assert "ALLOW_MODEL_ESCALATION=true" in persisted
    assert "ESCALATION_PROVIDER=openai" in persisted
    assert "ESCALATION_BUDGET_USD=0.0" in persisted
    assert "ALLOW_OLLAMA_ESCALATION=true" in persisted
    assert "OLLAMA_MODEL=llama3.2" in persisted
    assert "OLLAMA_BASE_URL=http://host.docker.internal:11434" in persisted

    assert response.headers.get("X-Settings-Restart-Required") == "true"
    restart_fields_header = response.headers.get("X-Settings-Restart-Required-Fields", "")
    restart_fields = [item for item in restart_fields_header.split(",") if item]
    assert "hardware_profile" in restart_fields

    hot_applied_header = response.headers.get("X-Settings-Hot-Applied-Fields", "")
    hot_applied_fields = [item for item in hot_applied_header.split(",") if item]
    assert "hardware_profile" not in hot_applied_fields
    assert set(hot_applied_fields) == {
        "log_level",
        "redact_pii_queries",
        "redact_pii_results",
        "allow_external_search",
        "default_search_provider",
        "cache_enabled",
        "allow_model_escalation",
        "escalation_provider",
        "allow_ollama_escalation",
        "ollama_model",
    }


def test_settings_write_endpoint_rejects_invalid_value_without_partial_write(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    original = "\n".join(
        [
            "APP_NAME=JARVISv5",
            "DEBUG=true",
            "HARDWARE_PROFILE=medium",
            "LOG_LEVEL=INFO",
            "ALLOW_EXTERNAL_SEARCH=false",
            "ALLOW_PAID_SEARCH=false",
            "DEFAULT_SEARCH_PROVIDER=duckduckgo",
            "SEARCH_SEARXNG_URL=http://searxng:8080/search",
            "TAVILY_API_KEY=",
            "CACHE_ENABLED=false",
            "ALLOW_MODEL_ESCALATION=false",
            "ESCALATION_PROVIDER=",
            "ESCALATION_BUDGET_USD=0.0",
            "ALLOW_OLLAMA_ESCALATION=false",
            "OLLAMA_BASE_URL=http://host.docker.internal:11434",
            "OLLAMA_MODEL=",
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


def test_settings_write_endpoint_rejects_invalid_escalation_provider_without_partial_write(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    original = "\n".join(
        [
            "APP_NAME=JARVISv5",
            "DEBUG=true",
            "HARDWARE_PROFILE=medium",
            "LOG_LEVEL=INFO",
            "ALLOW_EXTERNAL_SEARCH=false",
            "ALLOW_PAID_SEARCH=false",
            "DEFAULT_SEARCH_PROVIDER=duckduckgo",
            "SEARCH_SEARXNG_URL=http://searxng:8080/search",
            "TAVILY_API_KEY=",
            "CACHE_ENABLED=false",
            "ALLOW_MODEL_ESCALATION=false",
            "ESCALATION_PROVIDER=",
            "ESCALATION_BUDGET_USD=0.0",
            "ALLOW_OLLAMA_ESCALATION=false",
            "OLLAMA_BASE_URL=http://host.docker.internal:11434",
            "OLLAMA_MODEL=",
        ]
    ) + "\n"
    _write_env(env_path, original)
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/settings",
        json={
            "escalation_provider": "not-supported",
        },
    )

    assert response.status_code == 422
    assert _read_env(env_path) == original


def test_settings_write_endpoint_rejects_escalation_budget_update_without_partial_write(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    original = "\n".join(
        [
            "APP_NAME=JARVISv5",
            "DEBUG=true",
            "HARDWARE_PROFILE=medium",
            "LOG_LEVEL=INFO",
            "ALLOW_EXTERNAL_SEARCH=false",
            "ALLOW_PAID_SEARCH=false",
            "DEFAULT_SEARCH_PROVIDER=duckduckgo",
            "SEARCH_SEARXNG_URL=http://searxng:8080/search",
            "TAVILY_API_KEY=",
            "CACHE_ENABLED=false",
            "ALLOW_MODEL_ESCALATION=false",
            "ESCALATION_PROVIDER=",
            "ESCALATION_BUDGET_USD=0.0",
            "ALLOW_OLLAMA_ESCALATION=false",
            "OLLAMA_BASE_URL=http://host.docker.internal:11434",
            "OLLAMA_MODEL=",
        ]
    ) + "\n"
    _write_env(env_path, original)
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/settings",
        json={
            "escalation_budget_usd": 1.75,
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


def test_settings_write_endpoint_rejects_ollama_base_url_update_without_partial_write(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    original = "\n".join(
        [
            "APP_NAME=JARVISv5",
            "DEBUG=true",
            "HARDWARE_PROFILE=medium",
            "LOG_LEVEL=INFO",
            "ALLOW_EXTERNAL_SEARCH=false",
            "ALLOW_PAID_SEARCH=false",
            "DEFAULT_SEARCH_PROVIDER=duckduckgo",
            "SEARCH_SEARXNG_URL=http://searxng:8080/search",
            "TAVILY_API_KEY=",
            "CACHE_ENABLED=false",
            "ALLOW_MODEL_ESCALATION=false",
            "ESCALATION_PROVIDER=",
            "ESCALATION_BUDGET_USD=0.0",
            "ALLOW_OLLAMA_ESCALATION=false",
            "OLLAMA_BASE_URL=http://host.docker.internal:11434",
            "OLLAMA_MODEL=",
        ]
    ) + "\n"
    _write_env(env_path, original)
    monkeypatch.setattr("backend.api.main._SETTINGS_ENV_PATH", env_path)

    response = client.post(
        "/settings",
        json={
            "ollama_base_url": "http://localhost:11434",
        },
    )

    assert response.status_code == 422
    assert _read_env(env_path) == original
