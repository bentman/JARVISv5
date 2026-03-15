from __future__ import annotations

from backend.config.api_keys import SUPPORTED_PROVIDERS
from backend.models.providers import (
    AnthropicEscalationProvider,
    GeminiEscalationProvider,
    GrokEscalationProvider,
    OllamaEscalationProvider,
    OpenAIEscalationProvider,
)


def test_provider_names_match_supported_providers() -> None:
    providers = [
        AnthropicEscalationProvider(),
        OpenAIEscalationProvider(),
        GeminiEscalationProvider(),
        GrokEscalationProvider(),
    ]
    for provider in providers:
        assert provider.name in SUPPORTED_PROVIDERS


def test_all_providers_registered() -> None:
    providers = [
        AnthropicEscalationProvider(),
        OpenAIEscalationProvider(),
        GeminiEscalationProvider(),
        GrokEscalationProvider(),
    ]
    assert {provider.name for provider in providers} == SUPPORTED_PROVIDERS


def test_anthropic_execute_success(monkeypatch) -> None:
    from backend.models.providers import anthropic_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            assert provider == "anthropic"
            return "key-anthropic"

    class _Block:
        text = "anthropic-output"

    class _Response:
        content = [_Block()]

    class _Client:
        class _Messages:
            @staticmethod
            def create(**kwargs):
                assert kwargs["model"] == "claude-opus-4-6"
                assert kwargs["max_tokens"] == 128
                assert kwargs["messages"][0]["content"] == "prompt"
                return _Response()

        def __init__(self, api_key: str) -> None:
            assert api_key == "key-anthropic"
            self.messages = self._Messages()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.anthropic, "Anthropic", _Client)

    ok, output, error = AnthropicEscalationProvider().execute("prompt", 128, 7)
    assert ok is True
    assert output == "anthropic-output"
    assert error == ""


def test_anthropic_execute_exception(monkeypatch) -> None:
    from backend.models.providers import anthropic_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            _ = provider
            return "key-anthropic"

    class _Client:
        class _Messages:
            @staticmethod
            def create(**kwargs):
                _ = kwargs
                raise RuntimeError("anthropic-failure")

        def __init__(self, api_key: str) -> None:
            _ = api_key
            self.messages = self._Messages()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.anthropic, "Anthropic", _Client)

    ok, output, error = AnthropicEscalationProvider().execute("prompt", 128, None)
    assert ok is False
    assert output == ""
    assert "anthropic-failure" in error


def test_openai_execute_success(monkeypatch) -> None:
    from backend.models.providers import openai_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            assert provider == "openai"
            return "key-openai"

    class _Message:
        content = "openai-output"

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["max_tokens"] == 64
            assert kwargs["messages"][0]["content"] == "prompt"
            assert kwargs["seed"] == 11
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, api_key: str) -> None:
            assert api_key == "key-openai"
            self.chat = _Chat()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.openai, "OpenAI", _Client)

    ok, output, error = OpenAIEscalationProvider().execute("prompt", 64, 11)
    assert ok is True
    assert output == "openai-output"
    assert error == ""


def test_openai_execute_exception(monkeypatch) -> None:
    from backend.models.providers import openai_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            _ = provider
            return "key-openai"

    class _Completions:
        @staticmethod
        def create(**kwargs):
            _ = kwargs
            raise RuntimeError("openai-failure")

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, api_key: str) -> None:
            _ = api_key
            self.chat = _Chat()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.openai, "OpenAI", _Client)

    ok, output, error = OpenAIEscalationProvider().execute("prompt", 64, None)
    assert ok is False
    assert output == ""
    assert "openai-failure" in error


def test_gemini_execute_success(monkeypatch) -> None:
    from backend.models.providers import gemini_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            assert provider == "gemini"
            return "key-gemini"

    class _Response:
        text = "gemini-output"

    class _Models:
        @staticmethod
        def generate_content(*, model: str, contents: str):
            assert model == "gemini-2.0-flash"
            assert contents == "prompt"
            return _Response()

    class _Client:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "key-gemini"
            self.models = _Models()

    class _GenAIModule:
        Client = _Client

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module, "_get_genai_module", lambda: _GenAIModule)

    ok, output, error = GeminiEscalationProvider().execute("prompt", 256, 3)
    assert ok is True
    assert output == "gemini-output"
    assert error == ""


def test_gemini_execute_exception(monkeypatch) -> None:
    from backend.models.providers import gemini_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            _ = provider
            return "key-gemini"

    class _Models:
        @staticmethod
        def generate_content(*, model: str, contents: str):
            _ = model
            _ = contents
            raise RuntimeError("gemini-failure")

    class _Client:
        def __init__(self, *, api_key: str) -> None:
            _ = api_key
            self.models = _Models()

    class _GenAIModule:
        Client = _Client

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module, "_get_genai_module", lambda: _GenAIModule)

    ok, output, error = GeminiEscalationProvider().execute("prompt", 256, None)
    assert ok is False
    assert output == ""
    assert "gemini-failure" in error


def test_grok_execute_success(monkeypatch) -> None:
    from backend.models.providers import grok_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            assert provider == "grok"
            return "key-grok"

    class _Message:
        content = "grok-output"

    class _Choice:
        message = _Message()

    class _Response:
        choices = [_Choice()]

    class _Completions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == "grok-3"
            assert kwargs["max_tokens"] == 96
            assert kwargs["messages"][0]["content"] == "prompt"
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            assert api_key == "key-grok"
            assert base_url == "https://api.x.ai/v1"
            self.chat = _Chat()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.openai, "OpenAI", _Client)

    ok, output, error = GrokEscalationProvider().execute("prompt", 96, 1)
    assert ok is True
    assert output == "grok-output"
    assert error == ""


def test_grok_execute_exception(monkeypatch) -> None:
    from backend.models.providers import grok_provider as module

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            _ = provider
            return "key-grok"

    class _Completions:
        @staticmethod
        def create(**kwargs):
            _ = kwargs
            raise RuntimeError("grok-failure")

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            _ = api_key
            _ = base_url
            self.chat = _Chat()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.openai, "OpenAI", _Client)

    ok, output, error = GrokEscalationProvider().execute("prompt", 96, None)
    assert ok is False
    assert output == ""
    assert "grok-failure" in error


def test_api_key_lookup_happens_at_execute_time(monkeypatch) -> None:
    from backend.models.providers import openai_provider as module

    calls: list[str] = []

    class _Registry:
        def get_api_key(self, provider: str) -> str:
            calls.append(provider)
            return "dynamic-key"

    class _Response:
        choices = []

    class _Completions:
        @staticmethod
        def create(**kwargs):
            _ = kwargs
            return _Response()

    class _Chat:
        completions = _Completions()

    class _Client:
        def __init__(self, api_key: str) -> None:
            assert api_key == "dynamic-key"
            self.chat = _Chat()

    monkeypatch.setattr(module, "ApiKeyRegistry", lambda: _Registry())
    monkeypatch.setattr(module.openai, "OpenAI", _Client)

    provider = OpenAIEscalationProvider()
    assert calls == []
    provider.execute("prompt", 32, 4)
    assert calls == ["openai"]


def test_ollama_execute_success(monkeypatch) -> None:
    from backend.models.providers import ollama_provider as module

    class _Settings:
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "llama3.2"

    class _Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"response": "ollama-output"}

    def _post(url: str, *, json: dict, timeout: float):
        assert url == "http://host.docker.internal:11434/api/generate"
        assert json["model"] == "llama3.2"
        assert json["prompt"] == "prompt"
        assert json["stream"] is False
        assert json["options"]["num_predict"] == 77
        assert timeout == 30.0
        return _Response()

    monkeypatch.setattr(module, "Settings", lambda: _Settings())
    monkeypatch.setattr(module.httpx, "post", _post)

    ok, output, error = OllamaEscalationProvider().execute("prompt", 77, 123)
    assert ok is True
    assert output == "ollama-output"
    assert error == ""


def test_ollama_execute_unreachable(monkeypatch) -> None:
    from backend.models.providers import ollama_provider as module

    class _Settings:
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "llama3.2"

    def _post(url: str, *, json: dict, timeout: float):
        _ = url
        _ = json
        _ = timeout
        raise module.httpx.RequestError("connect failure")

    monkeypatch.setattr(module, "Settings", lambda: _Settings())
    monkeypatch.setattr(module.httpx, "post", _post)

    ok, output, error = OllamaEscalationProvider().execute("prompt", 55, None)
    assert ok is False
    assert output == ""
    assert error == "ollama_unreachable"


def test_ollama_execute_missing_model(monkeypatch) -> None:
    from backend.models.providers import ollama_provider as module

    class _Settings:
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "   "

    calls: list[str] = []

    def _post(url: str, *, json: dict, timeout: float):
        calls.append(url)
        _ = json
        _ = timeout
        return None

    monkeypatch.setattr(module, "Settings", lambda: _Settings())
    monkeypatch.setattr(module.httpx, "post", _post)

    ok, output, error = OllamaEscalationProvider().execute("prompt", 20, None)
    assert ok is False
    assert output == ""
    assert error == "ollama_model_not_configured"
    assert calls == []


def test_ollama_execute_timeout_maps_to_unreachable(monkeypatch) -> None:
    from backend.models.providers import ollama_provider as module

    class _Settings:
        OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        OLLAMA_MODEL = "llama3.2"

    def _post(url: str, *, json: dict, timeout: float):
        _ = url
        _ = json
        _ = timeout
        raise module.httpx.TimeoutException("timeout")

    monkeypatch.setattr(module, "Settings", lambda: _Settings())
    monkeypatch.setattr(module.httpx, "post", _post)

    ok, output, error = OllamaEscalationProvider().execute("prompt", 55, None)
    assert ok is False
    assert output == ""
    assert error == "ollama_unreachable"


def test_ollama_not_in_cloud_escalation_registry() -> None:
    from backend.controller import controller_service as controller_service_module

    assert "ollama" not in controller_service_module._ESCALATION_PROVIDER_REGISTRY
