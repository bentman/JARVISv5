from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "JARVISv5"
    DEBUG: bool = True
    HARDWARE_PROFILE: str = "Medium"
    LOG_LEVEL: str = "INFO"
    MODEL_PATH: str = "models/"
    DATA_PATH: str = "data/"
    BACKEND_PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
