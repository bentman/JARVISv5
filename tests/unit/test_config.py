import pytest

from backend.config.settings import (
    EDITABLE_SETTINGS_ENV_KEYS,
    Settings,
    get_safe_config_projection,
    normalize_escalation_provider,
    persist_settings_updates,
    serialize_editable_setting_value,
)


def test_settings_defaults_app_name() -> None:
    settings = Settings()
    assert settings.APP_NAME == "JARVISv5"


def test_settings_defaults_debug_true() -> None:
    settings = Settings()
    assert settings.DEBUG is True


def test_settings_generation_seed_default_none() -> None:
    settings = Settings()
    assert settings.GENERATION_SEED is None


def test_settings_generation_seed_from_init() -> None:
    settings = Settings(GENERATION_SEED=42)
    assert settings.GENERATION_SEED == 42


def test_settings_search_field_defaults(monkeypatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    settings = Settings()
    assert settings.ALLOW_PAID_SEARCH is False
    assert settings.SEARCH_SEARXNG_URL == "http://searxng:8080/search"
    assert isinstance(settings.TAVILY_API_KEY, str)


def test_settings_search_field_overrides_from_init() -> None:
    settings = Settings(
        ALLOW_PAID_SEARCH=True,
        SEARCH_SEARXNG_URL="http://localhost:18080/search",
        TAVILY_API_KEY="demo-key",
    )
    assert settings.ALLOW_PAID_SEARCH is True
    assert settings.SEARCH_SEARXNG_URL == "http://localhost:18080/search"
    assert settings.TAVILY_API_KEY == "demo-key"


def test_settings_escalation_field_defaults() -> None:
    settings = Settings()
    assert settings.ALLOW_MODEL_ESCALATION is False
    assert settings.ESCALATION_PROVIDER == ""
    assert settings.ESCALATION_BUDGET_USD == 0.0


def test_settings_ollama_field_defaults(monkeypatch) -> None:
    settings = Settings(**{"_env_file": None})
    assert settings.ALLOW_OLLAMA_ESCALATION is False
    assert settings.OLLAMA_BASE_URL == "http://host.docker.internal:11434"
    assert settings.OLLAMA_MODEL == ""


def test_settings_escalation_field_overrides_from_init() -> None:
    settings = Settings(
        ALLOW_MODEL_ESCALATION=True,
        ESCALATION_PROVIDER="openai",
        ESCALATION_BUDGET_USD=3.5,
    )
    assert settings.ALLOW_MODEL_ESCALATION is True
    assert settings.ESCALATION_PROVIDER == "openai"
    assert settings.ESCALATION_BUDGET_USD == 3.5


def test_normalize_escalation_provider_accepts_supported_and_empty_values() -> None:
    assert normalize_escalation_provider(" OPENAI ") == "openai"
    assert normalize_escalation_provider("   ") == ""


def test_normalize_escalation_provider_rejects_unsupported_value() -> None:
    with pytest.raises(ValueError):
        normalize_escalation_provider("unsupported")


def test_safe_config_projection_includes_escalation_fields(monkeypatch) -> None:
    class _Registry:
        def get_configured_providers(self) -> list[str]:
            return ["anthropic", "openai"]

    monkeypatch.setattr("backend.config.settings.ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr("backend.config.settings.fetch_ollama_model_options", lambda _url: ["llama3.2", "mistral"])

    settings = Settings(
        **{"_env_file": None},
        ALLOW_MODEL_ESCALATION=True,
        ESCALATION_PROVIDER="openai",
        ESCALATION_BUDGET_USD=4.25,
    )
    projection = get_safe_config_projection(settings)

    assert projection["allow_model_escalation"] is True
    assert projection["escalation_provider"] == "openai"
    assert projection["escalation_budget_usd"] == 4.25
    assert projection["allow_ollama_escalation"] is False
    assert projection["ollama_base_url"] == "http://host.docker.internal:11434"
    assert projection["ollama_model"] == ""
    assert projection["ollama_model_options"] == ["llama3.2", "mistral"]
    assert projection["escalation_configured_providers"] == ["anthropic", "openai"]


def test_safe_config_projection_includes_ollama_overrides(monkeypatch) -> None:
    class _Registry:
        def get_configured_providers(self) -> list[str]:
            return []

    monkeypatch.setattr("backend.config.settings.ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr("backend.config.settings.fetch_ollama_model_options", lambda _url: ["llama3.2:latest"])

    settings = Settings(
        ALLOW_OLLAMA_ESCALATION=True,
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="llama3.2",
    )
    projection = get_safe_config_projection(settings)

    assert projection["allow_ollama_escalation"] is True
    assert projection["ollama_base_url"] == "http://localhost:11434"
    assert projection["ollama_model"] == "llama3.2"
    assert projection["ollama_model_options"] == ["llama3.2:latest"]


def test_persist_settings_updates_rejects_escalation_budget_write(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("ESCALATION_BUDGET_USD=0.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported editable setting: escalation_budget_usd"):
        persist_settings_updates(
            updates={"escalation_budget_usd": 3.0},
            env_path=env_path,
        )


def test_persist_settings_updates_accepts_ollama_editable_fields(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "ALLOW_OLLAMA_ESCALATION=false\n"
        "OLLAMA_MODEL=\n",
        encoding="utf-8",
    )

    persist_settings_updates(
        updates={
            "allow_ollama_escalation": True,
            "ollama_model": "llama3.2",
        },
        env_path=env_path,
    )

    updated = env_path.read_text(encoding="utf-8")
    assert "ALLOW_OLLAMA_ESCALATION=true" in updated
    assert "OLLAMA_MODEL=llama3.2" in updated


def test_persist_settings_updates_rejects_ollama_base_url_write(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_BASE_URL=http://host.docker.internal:11434\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported editable setting: ollama_base_url"):
        persist_settings_updates(
            updates={"ollama_base_url": "http://localhost:11434"},
            env_path=env_path,
        )


def test_editable_settings_env_keys_include_privacy_redaction_fields() -> None:
    assert EDITABLE_SETTINGS_ENV_KEYS["redact_pii_queries"] == "REDACT_PII_QUERIES"
    assert EDITABLE_SETTINGS_ENV_KEYS["redact_pii_results"] == "REDACT_PII_RESULTS"


def test_serialize_editable_setting_value_supports_privacy_redaction_booleans() -> None:
    assert serialize_editable_setting_value("redact_pii_queries", True) == "true"
    assert serialize_editable_setting_value("redact_pii_queries", False) == "false"
    assert serialize_editable_setting_value("redact_pii_results", True) == "true"
    assert serialize_editable_setting_value("redact_pii_results", False) == "false"


def test_persist_settings_updates_accepts_privacy_redaction_fields(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "REDACT_PII_QUERIES=true\n"
        "REDACT_PII_RESULTS=false\n",
        encoding="utf-8",
    )

    persist_settings_updates(
        updates={
            "redact_pii_queries": False,
            "redact_pii_results": True,
        },
        env_path=env_path,
    )

    updated = env_path.read_text(encoding="utf-8")
    assert "REDACT_PII_QUERIES=false" in updated
    assert "REDACT_PII_RESULTS=true" in updated


def test_safe_config_projection_includes_retrieval_fields(monkeypatch) -> None:
    class _Registry:
        def get_configured_providers(self) -> list[str]:
            return []

    monkeypatch.setattr("backend.config.settings.ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr("backend.config.settings.fetch_ollama_model_options", lambda _url: [])

    settings = Settings(
        RETRIEVAL_MAX_RESULTS=15,
        RETRIEVAL_MIN_SCORE=0.2,
        RETRIEVAL_TIME_DECAY_TAU_HOURS=30.0,
    )
    projection = get_safe_config_projection(settings)

    assert projection["retrieval_max_results"] == 15
    assert projection["retrieval_min_score"] == 0.2
    assert projection["retrieval_time_decay_tau_hours"] == 30.0


def test_serialize_editable_setting_value_supports_retrieval_fields() -> None:
    assert serialize_editable_setting_value("retrieval_max_results", 12) == "12"
    assert serialize_editable_setting_value("retrieval_min_score", 0.25) == "0.25"
    assert (
        serialize_editable_setting_value("retrieval_time_decay_tau_hours", 18.0)
        == "18.0"
    )


def test_serialize_editable_setting_value_rejects_invalid_retrieval_fields() -> None:
    with pytest.raises(ValueError, match="retrieval_max_results must be >= 1"):
        serialize_editable_setting_value("retrieval_max_results", 0)

    with pytest.raises(ValueError, match=r"retrieval_min_score must be within \[0.0, 1.0\]"):
        serialize_editable_setting_value("retrieval_min_score", 1.1)

    with pytest.raises(ValueError, match="retrieval_time_decay_tau_hours must be > 0"):
        serialize_editable_setting_value("retrieval_time_decay_tau_hours", 0.0)


def test_persist_settings_updates_accepts_retrieval_fields(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "RETRIEVAL_MAX_RESULTS=10\n"
        "RETRIEVAL_MIN_SCORE=0.0\n"
        "RETRIEVAL_TIME_DECAY_TAU_HOURS=24.0\n",
        encoding="utf-8",
    )

    persist_settings_updates(
        updates={
            "retrieval_max_results": 20,
            "retrieval_min_score": 0.3,
            "retrieval_time_decay_tau_hours": 40.0,
        },
        env_path=env_path,
    )

    updated = env_path.read_text(encoding="utf-8")
    assert "RETRIEVAL_MAX_RESULTS=20" in updated
    assert "RETRIEVAL_MIN_SCORE=0.3" in updated
    assert "RETRIEVAL_TIME_DECAY_TAU_HOURS=40.0" in updated
