"""Centralized cache settings (M6.6)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from backend.config.settings import Settings


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class CacheSettings:
    cache_enabled: bool
    redis_url: str
    cache_default_ttl: int
    context_cache_ttl_seconds: int
    tool_cache_ttl_seconds: int


def load_cache_settings() -> CacheSettings:
    """Load cache settings from canonical typed settings + env TTL overrides."""
    settings = Settings()

    return CacheSettings(
        cache_enabled=bool(settings.CACHE_ENABLED),
        redis_url=str(settings.REDIS_URL),
        cache_default_ttl=_parse_positive_int(os.getenv("CACHE_DEFAULT_TTL"), default=3600),
        context_cache_ttl_seconds=_parse_positive_int(os.getenv("CONTEXT_CACHE_TTL_SECONDS"), default=3600),
        tool_cache_ttl_seconds=_parse_positive_int(os.getenv("TOOL_CACHE_TTL_SECONDS"), default=1800),
    )
