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
