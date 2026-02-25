from backend.cache.settings import load_cache_settings, parse_bool


def test_parse_bool_true_values_case_insensitive() -> None:
    for value in ("1", "true", "TRUE", "Yes", "on", " On "):
        assert parse_bool(value, default=False) is True


def test_parse_bool_false_values_case_insensitive() -> None:
    for value in ("0", "false", "FALSE", "No", "off", " Off "):
        assert parse_bool(value, default=True) is False


def test_parse_bool_invalid_uses_default() -> None:
    assert parse_bool("maybe", default=True) is True
    assert parse_bool("", default=False) is False
    assert parse_bool(None, default=True) is True


def test_load_cache_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("CACHE_ENABLED", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CACHE_DEFAULT_TTL", raising=False)
    monkeypatch.delenv("CONTEXT_CACHE_TTL_SECONDS", raising=False)
    monkeypatch.delenv("TOOL_CACHE_TTL_SECONDS", raising=False)

    settings = load_cache_settings()
    assert settings.cache_enabled is True
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cache_default_ttl == 3600
    assert settings.context_cache_ttl_seconds == 3600
    assert settings.tool_cache_ttl_seconds == 1800


def test_load_cache_settings_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_ENABLED", "off")
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("CACHE_DEFAULT_TTL", "120")
    monkeypatch.setenv("CONTEXT_CACHE_TTL_SECONDS", "45")
    monkeypatch.setenv("TOOL_CACHE_TTL_SECONDS", "90")

    settings = load_cache_settings()
    assert settings.cache_enabled is False
    assert settings.redis_url == "redis://cache:6379/1"
    assert settings.cache_default_ttl == 120
    assert settings.context_cache_ttl_seconds == 45
    assert settings.tool_cache_ttl_seconds == 90
