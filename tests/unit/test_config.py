from backend.config.settings import Settings


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
