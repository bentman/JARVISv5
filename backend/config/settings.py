import os
from pathlib import Path
from typing import TypedDict

import httpx
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

from backend.config.api_keys import ApiKeyRegistry, SUPPORTED_PROVIDERS


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
    ALLOW_PAID_SEARCH: bool = False
    DEFAULT_SEARCH_PROVIDER: str = "duckduckgo"
    SEARCH_SEARXNG_URL: str = "http://searxng:8080/search"
    TAVILY_API_KEY: str = ""
    CACHE_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOW_MODEL_ESCALATION: bool = False
    ESCALATION_PROVIDER: str = ""
    ESCALATION_BUDGET_USD: float = 0.0
    ALLOW_OLLAMA_ESCALATION: bool = False
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = ""
    RETRIEVAL_MAX_RESULTS: int = 10
    RETRIEVAL_MIN_SCORE: float = 0.0
    RETRIEVAL_TIME_DECAY_TAU_HOURS: float = 24.0
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
    allow_paid_search: bool
    default_search_provider: str
    searxng_url: str
    tavily_key_configured: bool
    cache_enabled: bool
    allow_model_escalation: bool
    escalation_provider: str
    escalation_budget_usd: float
    allow_ollama_escalation: bool
    ollama_base_url: str
    ollama_model: str
    retrieval_max_results: int
    retrieval_min_score: float
    retrieval_time_decay_tau_hours: float
    ollama_model_options: list[str]
    escalation_configured_providers: list[str]


def fetch_ollama_model_options(ollama_base_url: str) -> list[str]:
    base_url = str(ollama_base_url or "").strip().rstrip("/")
    if not base_url:
        return []

    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
    except Exception:
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except Exception:
        return []

    models_raw = payload.get("models", []) if isinstance(payload, dict) else []
    if not isinstance(models_raw, list):
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in models_raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("model") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)

    return out


def get_safe_config_projection(settings: Settings) -> SafeConfigProjection:
    api_keys = ApiKeyRegistry()
    ollama_model_options = fetch_ollama_model_options(settings.OLLAMA_BASE_URL)
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
        "allow_paid_search": settings.ALLOW_PAID_SEARCH,
        "default_search_provider": settings.DEFAULT_SEARCH_PROVIDER,
        "searxng_url": settings.SEARCH_SEARXNG_URL,
        "tavily_key_configured": bool(str(settings.TAVILY_API_KEY).strip()),
        "cache_enabled": settings.CACHE_ENABLED,
        "allow_model_escalation": settings.ALLOW_MODEL_ESCALATION,
        "escalation_provider": normalize_escalation_provider(settings.ESCALATION_PROVIDER),
        "escalation_budget_usd": float(settings.ESCALATION_BUDGET_USD),
        "allow_ollama_escalation": settings.ALLOW_OLLAMA_ESCALATION,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "retrieval_max_results": int(settings.RETRIEVAL_MAX_RESULTS),
        "retrieval_min_score": float(settings.RETRIEVAL_MIN_SCORE),
        "retrieval_time_decay_tau_hours": float(settings.RETRIEVAL_TIME_DECAY_TAU_HOURS),
        "ollama_model_options": ollama_model_options,
        "escalation_configured_providers": api_keys.get_configured_providers(),
    }


EDITABLE_SETTINGS_ENV_KEYS: dict[str, str] = {
    "hardware_profile": "HARDWARE_PROFILE",
    "log_level": "LOG_LEVEL",
    "redact_pii_queries": "REDACT_PII_QUERIES",
    "redact_pii_results": "REDACT_PII_RESULTS",
    "allow_external_search": "ALLOW_EXTERNAL_SEARCH",
    "default_search_provider": "DEFAULT_SEARCH_PROVIDER",
    "cache_enabled": "CACHE_ENABLED",
    "allow_model_escalation": "ALLOW_MODEL_ESCALATION",
    "escalation_provider": "ESCALATION_PROVIDER",
    "allow_ollama_escalation": "ALLOW_OLLAMA_ESCALATION",
    "ollama_model": "OLLAMA_MODEL",
    "retrieval_max_results": "RETRIEVAL_MAX_RESULTS",
    "retrieval_min_score": "RETRIEVAL_MIN_SCORE",
    "retrieval_time_decay_tau_hours": "RETRIEVAL_TIME_DECAY_TAU_HOURS",
}

ALLOWED_HARDWARE_PROFILES = {"light", "medium", "heavy", "test", "npu-optimized"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
ALLOWED_DEFAULT_SEARCH_PROVIDERS = {"searxng", "duckduckgo", "tavily"}


def normalize_hardware_profile(value: str) -> str:
    normalized = str(value).strip().lower().replace("_", "-")
    if normalized not in ALLOWED_HARDWARE_PROFILES:
        allowed = ", ".join(sorted(ALLOWED_HARDWARE_PROFILES))
        raise ValueError(f"hardware_profile must be one of: {allowed}")
    return normalized


def normalize_log_level(value: str) -> str:
    normalized = str(value).strip().upper()
    if normalized not in ALLOWED_LOG_LEVELS:
        allowed = ", ".join(sorted(ALLOWED_LOG_LEVELS))
        raise ValueError(f"log_level must be one of: {allowed}")
    return normalized


def normalize_default_search_provider(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in ALLOWED_DEFAULT_SEARCH_PROVIDERS:
        allowed = ", ".join(sorted(ALLOWED_DEFAULT_SEARCH_PROVIDERS))
        raise ValueError(f"default_search_provider must be one of: {allowed}")
    return normalized


def normalize_escalation_provider(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized == "":
        return ""
    if normalized not in SUPPORTED_PROVIDERS:
        allowed = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ValueError(f"escalation_provider must be one of: {allowed}")
    return normalized


def serialize_editable_setting_value(field_name: str, value: object) -> str:
    if field_name not in EDITABLE_SETTINGS_ENV_KEYS:
        raise ValueError(f"unsupported editable setting: {field_name}")

    if field_name == "hardware_profile":
        return normalize_hardware_profile(str(value))
    if field_name == "log_level":
        return normalize_log_level(str(value))
    if field_name == "default_search_provider":
        return normalize_default_search_provider(str(value))
    if field_name == "escalation_provider":
        return normalize_escalation_provider(str(value))
    if field_name == "ollama_model":
        return str(value)
    if field_name == "retrieval_max_results":
        value_i = int(value)
        if value_i < 1:
            raise ValueError("retrieval_max_results must be >= 1")
        return str(value_i)
    if field_name == "retrieval_min_score":
        value_f = float(value)
        if value_f < 0.0 or value_f > 1.0:
            raise ValueError("retrieval_min_score must be within [0.0, 1.0]")
        return str(value_f)
    if field_name == "retrieval_time_decay_tau_hours":
        value_f = float(value)
        if value_f <= 0.0:
            raise ValueError("retrieval_time_decay_tau_hours must be > 0")
        return str(value_f)
    if field_name in {
        "redact_pii_queries",
        "redact_pii_results",
        "allow_external_search",
        "cache_enabled",
        "allow_model_escalation",
        "allow_ollama_escalation",
    }:
        return "true" if bool(value) else "false"

    raise ValueError(f"unsupported editable setting: {field_name}")


def persist_settings_updates(updates: dict[str, object], env_path: Path | None = None) -> None:
    """Atomically persist validated editable settings to .env."""
    if not updates:
        raise ValueError("no settings provided")

    target_path = env_path or Path(".env")
    serialized: dict[str, str] = {}
    for field_name, raw_value in updates.items():
        env_key = EDITABLE_SETTINGS_ENV_KEYS.get(field_name)
        if env_key is None:
            raise ValueError(f"unsupported editable setting: {field_name}")
        serialized[env_key] = serialize_editable_setting_value(field_name, raw_value)

    existing_lines = []
    if target_path.exists():
        existing_lines = target_path.read_text(encoding="utf-8").splitlines()

    out_lines: list[str] = []
    touched_keys: set[str] = set()

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            out_lines.append(line)
            continue

        key, _ = line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in serialized:
            out_lines.append(f"{normalized_key}={serialized[normalized_key]}")
            touched_keys.add(normalized_key)
        else:
            out_lines.append(line)

    for key, value in serialized.items():
        if key not in touched_keys:
            out_lines.append(f"{key}={value}")

    content = "\n".join(out_lines) + "\n"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f"{target_path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, target_path)


def settings_update_restart_semantics(updated_fields: set[str]) -> dict[str, object]:
    """Restart semantics for editable settings updates.

    Roadmap T11.3.1 requires profile/model-affecting values to be restart-required.
    """
    restart_required_fields: list[str] = []
    if "hardware_profile" in updated_fields:
        restart_required_fields.append("hardware_profile")

    hot_applied_fields = sorted(
        field
        for field in updated_fields
        if field in EDITABLE_SETTINGS_ENV_KEYS and field not in set(restart_required_fields)
    )

    return {
        "restart_required": len(restart_required_fields) > 0,
        "restart_required_fields": restart_required_fields,
        "hot_applied_fields": hot_applied_fields,
    }
