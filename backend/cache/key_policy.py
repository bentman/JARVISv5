"""Deterministic cache key and JSON serialization helpers (M6.2)."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def dumps_json(obj: Any) -> str:
    """Serialize JSON with stable ordering and ASCII-safe output."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def loads_json(text: str) -> Any:
    """Deserialize JSON text."""
    return json.loads(text)


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite float values are not allowed in cache key parts")
        # Stable textual representation for cross-run/platform determinism.
        return {"__float__": repr(value)}

    if isinstance(value, list):
        return [_normalize_value(item) for item in value]

    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise TypeError("Dictionary keys for cache key parts must be strings")
            normalized[key] = _normalize_value(value[key])
        return normalized

    raise TypeError(f"Unsupported value type for cache key parts: {type(value).__name__}")


def make_cache_key(
    prefix: str,
    *,
    parts: dict[str, Any] | list[tuple[str, Any]],
    version: str = "v1",
    max_key_length: int = 200,
) -> str:
    """Build deterministic cache keys with version tag and hash fallback.

    Key form:
      - direct: {prefix}:{version}:{serialized_parts}
      - hashed: {prefix}:{version}:h:{sha256_hex}
    """
    if not isinstance(prefix, str) or prefix == "":
        raise ValueError("prefix must be a non-empty string")
    if not isinstance(version, str) or version == "":
        raise ValueError("version must be a non-empty string")
    if not isinstance(max_key_length, int) or max_key_length <= 0:
        raise ValueError("max_key_length must be a positive integer")

    if isinstance(parts, dict):
        ordered_items: list[tuple[str, Any]] = [(k, parts[k]) for k in sorted(parts.keys())]
    else:
        ordered_items = list(parts)

    normalized_items: list[list[Any]] = []
    for key, value in ordered_items:
        if not isinstance(key, str):
            raise TypeError("Cache key part names must be strings")
        normalized_items.append([key, _normalize_value(value)])

    serialized_parts = dumps_json(normalized_items)
    direct_key = f"{prefix}:{version}:{serialized_parts}"
    if len(direct_key) <= max_key_length:
        return direct_key

    digest = hashlib.sha256(direct_key.encode("utf-8")).hexdigest()
    return f"{prefix}:{version}:h:{digest}"
