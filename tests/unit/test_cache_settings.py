from types import SimpleNamespace

from backend.cache.settings import load_cache_settings


def test_load_cache_settings_uses_typed_settings_for_enablement_and_redis_url(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_ENABLED", "off")
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/9")
    monkeypatch.delenv("CACHE_DEFAULT_TTL", raising=False)
    monkeypatch.delenv("CONTEXT_CACHE_TTL_SECONDS", raising=False)
    monkeypatch.delenv("TOOL_CACHE_TTL_SECONDS", raising=False)

    monkeypatch.setattr(
        "backend.cache.settings.Settings",
        lambda: SimpleNamespace(CACHE_ENABLED=True, REDIS_URL="redis://typed:6379/1"),
    )

    settings = load_cache_settings()
    assert settings.cache_enabled is True
    assert settings.redis_url == "redis://typed:6379/1"
    assert settings.cache_default_ttl == 3600
    assert settings.context_cache_ttl_seconds == 3600
    assert settings.tool_cache_ttl_seconds == 1800


def test_load_cache_settings_ttl_env_overrides(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.cache.settings.Settings",
        lambda: SimpleNamespace(CACHE_ENABLED=False, REDIS_URL="redis://typed:6379/2"),
    )

    monkeypatch.setenv("CACHE_DEFAULT_TTL", "120")
    monkeypatch.setenv("CONTEXT_CACHE_TTL_SECONDS", "45")
    monkeypatch.setenv("TOOL_CACHE_TTL_SECONDS", "90")

    settings = load_cache_settings()
    assert settings.cache_enabled is False
    assert settings.redis_url == "redis://typed:6379/2"
    assert settings.cache_default_ttl == 120
    assert settings.context_cache_ttl_seconds == 45
    assert settings.tool_cache_ttl_seconds == 90


def test_load_cache_settings_ttl_invalid_values_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.cache.settings.Settings",
        lambda: SimpleNamespace(CACHE_ENABLED=False, REDIS_URL="redis://typed:6379/3"),
    )

    monkeypatch.setenv("CACHE_DEFAULT_TTL", "0")
    monkeypatch.setenv("CONTEXT_CACHE_TTL_SECONDS", "invalid")
    monkeypatch.setenv("TOOL_CACHE_TTL_SECONDS", "-1")

    settings = load_cache_settings()
    assert settings.cache_default_ttl == 3600
    assert settings.context_cache_ttl_seconds == 3600
    assert settings.tool_cache_ttl_seconds == 1800
