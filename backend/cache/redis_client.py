"""Redis cache client wrapper with fail-safe behavior."""
from __future__ import annotations

import json
from typing import Any, Callable

from backend.cache.settings import load_cache_settings

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


class RedisCacheClient:
    """Redis client with fail-safe fallback semantics."""

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        enabled: bool = True,
        default_ttl: int = 3600,
        redis_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.enabled = bool(enabled) and REDIS_AVAILABLE
        self.default_ttl = int(default_ttl)
        self._connection_failed = False
        self.client: Any | None = None

        if not self.enabled:
            return

        factory = redis_factory
        if factory is None:
            if redis is None:
                self._connection_failed = True
                return
            factory = redis.from_url

        try:
            self.client = factory(
                url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self.client.ping()
        except Exception:
            self.client = None
            self._connection_failed = True

    def get(self, key: str) -> str | None:
        if not self.enabled or self._connection_failed or self.client is None:
            return None
        try:
            value = self.client.get(key)
            return str(value) if value is not None else None
        except Exception:
            return None

    def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        if not self.enabled or self._connection_failed or self.client is None:
            return False
        try:
            ttl_seconds = int(ttl) if ttl is not None else self.default_ttl
            self.client.setex(key, ttl_seconds, value)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        if not self.enabled or self._connection_failed or self.client is None:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        if not self.enabled or self._connection_failed or self.client is None:
            return 0
        try:
            keys = list(self.client.scan_iter(match=pattern))
            if not keys:
                return 0
            deleted = self.client.delete(*keys)
            return int(deleted) if deleted is not None else 0
        except Exception:
            return 0

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self.get(key)
        if raw is None:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def set_json(self, key: str, value: dict[str, Any], ttl: int | None = None) -> bool:
        try:
            serialized = json.dumps(value, separators=(",", ":"))
        except TypeError:
            return False
        return self.set(key, serialized, ttl=ttl)

    def health_check(self) -> dict[str, Any]:
        # Stable, deterministic shape required.
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "message": "Caching disabled",
            }

        if self._connection_failed or self.client is None:
            return {
                "enabled": True,
                "connected": False,
                "message": "Connection unavailable",
            }

        try:
            self.client.ping()
            return {
                "enabled": True,
                "connected": True,
                "message": "Connected",
            }
        except Exception:
            return {
                "enabled": True,
                "connected": False,
                "message": "Connection unavailable",
            }


def create_default_redis_client() -> RedisCacheClient:
    """Create Redis cache client from environment variables."""
    settings = load_cache_settings()

    return RedisCacheClient(
        url=settings.redis_url,
        enabled=settings.cache_enabled,
        default_ttl=settings.cache_default_ttl,
    )