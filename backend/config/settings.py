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
