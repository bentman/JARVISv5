from backend.config.settings import Settings


def test_settings_defaults_app_name() -> None:
    settings = Settings()
    assert settings.APP_NAME == "JARVISv5"


def test_settings_defaults_debug_true() -> None:
    settings = Settings()
    assert settings.DEBUG is True
