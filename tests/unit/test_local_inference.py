import pytest

from backend.models.local_inference import LocalInferenceClient


def test_llama_cpp_import() -> None:
    llama_cpp = pytest.importorskip("llama_cpp")
    assert llama_cpp is not None


def test_local_inference_client_instantiation() -> None:
    client = LocalInferenceClient(model_path="models/dummy.gguf")
    assert client.model_path == "models/dummy.gguf"
    assert client.model is None


def test_generate_without_load_raises_runtime_error() -> None:
    client = LocalInferenceClient(model_path="models/dummy.gguf")
    with pytest.raises(RuntimeError):
        client.generate("hello")


def test_generate_passes_seed_when_provided() -> None:
    class _StubModel:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def create_completion(self, prompt: str, **kwargs):
            self.calls.append((prompt, dict(kwargs)))
            return {"choices": [{"text": "ok"}]}

    client = LocalInferenceClient(model_path="models/dummy.gguf")
    stub = _StubModel()
    client.model = stub

    out = client.generate("hello", max_tokens=12, seed=42)

    assert out == "ok"
    assert len(stub.calls) == 1
    prompt, kwargs = stub.calls[0]
    assert prompt == "hello"
    assert kwargs["max_tokens"] == 12
    assert kwargs["echo"] is False
    assert kwargs["seed"] == 42


def test_generate_omits_seed_when_not_provided() -> None:
    class _StubModel:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def create_completion(self, prompt: str, **kwargs):
            self.calls.append((prompt, dict(kwargs)))
            return {"choices": [{"text": "ok"}]}

    client = LocalInferenceClient(model_path="models/dummy.gguf")
    stub = _StubModel()
    client.model = stub

    out = client.generate("hello", max_tokens=12)

    assert out == "ok"
    assert len(stub.calls) == 1
    prompt, kwargs = stub.calls[0]
    assert prompt == "hello"
    assert kwargs["max_tokens"] == 12
    assert kwargs["echo"] is False
    assert "seed" not in kwargs
