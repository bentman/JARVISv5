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
