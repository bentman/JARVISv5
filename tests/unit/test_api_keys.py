from backend.config.api_keys import ApiKeyRegistry


def test_get_configured_providers_returns_empty_when_no_keys_set(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    registry = ApiKeyRegistry()

    assert registry.get_configured_providers() == []


def test_get_configured_providers_returns_only_populated_keys(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROK_API_KEY", "   ")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    registry = ApiKeyRegistry()

    assert registry.get_configured_providers() == ["anthropic", "openai"]


def test_get_api_key_returns_empty_string_for_unconfigured_provider(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    registry = ApiKeyRegistry()

    assert registry.get_api_key("openai") == ""
    assert registry.get_api_key("unknown") == ""


def test_get_api_key_returns_value_for_configured_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    registry = ApiKeyRegistry()

    assert registry.get_api_key("openai") == "openai-key"
    assert registry.get_api_key(" OPENAI ") == "openai-key"


def test_get_configured_providers_is_deterministic(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    registry_a = ApiKeyRegistry()
    registry_b = ApiKeyRegistry()

    assert registry_a.get_configured_providers() == ["anthropic", "gemini"]
    assert registry_b.get_configured_providers() == ["anthropic", "gemini"]
