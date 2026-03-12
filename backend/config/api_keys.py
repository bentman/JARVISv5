import os


SUPPORTED_PROVIDERS: frozenset[str] = frozenset({
    "anthropic",
    "gemini",
    "grok",
    "openai",
})


_PROVIDER_ENV_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "grok": "GROK_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class ApiKeyRegistry:
    """Read-only API key registry for model escalation providers."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {
            provider: str(os.getenv(env_key, ""))
            for provider, env_key in _PROVIDER_ENV_KEYS.items()
        }

    def get_configured_providers(self) -> list[str]:
        return sorted(
            provider
            for provider, key in self._keys.items()
            if str(key).strip()
        )

    def get_api_key(self, provider: str) -> str:
        normalized = str(provider).strip().lower()
        if normalized not in SUPPORTED_PROVIDERS:
            return ""
        return str(self._keys.get(normalized, ""))
