"""Centralized cache settings (M6.6)."""
from __future__ import annotations

import os
from dataclasses import dataclass


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def parse_bool(value: str | None, default: bool = True) -> bool:
    """Parse common boolean env forms with deterministic fallback."""
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


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
    """Load cache settings from environment with safe defaults."""
    return CacheSettings(
        cache_enabled=parse_bool(os.getenv("CACHE_ENABLED"), default=True),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        cache_default_ttl=_parse_positive_int(os.getenv("CACHE_DEFAULT_TTL"), default=3600),
        context_cache_ttl_seconds=_parse_positive_int(os.getenv("CONTEXT_CACHE_TTL_SECONDS"), default=3600),
        tool_cache_ttl_seconds=_parse_positive_int(os.getenv("TOOL_CACHE_TTL_SECONDS"), default=1800),
    )
