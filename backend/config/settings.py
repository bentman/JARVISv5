from typing import TypedDict

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource


class Settings(BaseSettings):
    APP_NAME: str = "JARVISv5"
    DEBUG: bool = True
    HARDWARE_PROFILE: str = "Medium"
    LOG_LEVEL: str = "INFO"
    MODEL_PATH: str = "models/"
    DATA_PATH: str = "data/"
    BACKEND_PORT: int = 8000
    REDACT_PII_QUERIES: bool = True
    REDACT_PII_RESULTS: bool = False
    ALLOW_EXTERNAL_SEARCH: bool = False
    DEFAULT_SEARCH_PROVIDER: str = "duckduckgo"
    CACHE_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    DAILY_BUDGET_USD: float = 0.0
    MONTHLY_BUDGET_USD: float = 0.0
    GENERATION_SEED: int | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            true_values = {"1", "true", "yes", "on", "dev", "debug", "development"}
            false_values = {"0", "false", "no", "off", "release", "prod", "production"}

            if normalized in true_values:
                return True
            if normalized in false_values:
                return False

            accepted = sorted(true_values | false_values)
            raise ValueError(
                "Invalid DEBUG value. Accepted values: "
                + ", ".join(accepted)
            )

        raise ValueError("Invalid DEBUG value type. Expected bool or string.")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Deterministic precedence for this project:
        # init kwargs > .env file > OS environment > file secrets
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )


class SafeConfigProjection(TypedDict):
    app_name: str
    debug: bool
    hardware_profile: str
    log_level: str
    model_path: str
    data_path: str
    backend_port: int
    redact_pii_queries: bool
    redact_pii_results: bool
    allow_external_search: bool
    default_search_provider: str
    cache_enabled: bool


def get_safe_config_projection(settings: Settings) -> SafeConfigProjection:
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "hardware_profile": settings.HARDWARE_PROFILE,
        "log_level": settings.LOG_LEVEL,
        "model_path": settings.MODEL_PATH,
        "data_path": settings.DATA_PATH,
        "backend_port": settings.BACKEND_PORT,
        "redact_pii_queries": settings.REDACT_PII_QUERIES,
        "redact_pii_results": settings.REDACT_PII_RESULTS,
        "allow_external_search": settings.ALLOW_EXTERNAL_SEARCH,
        "default_search_provider": settings.DEFAULT_SEARCH_PROVIDER,
        "cache_enabled": settings.CACHE_ENABLED,
    }
