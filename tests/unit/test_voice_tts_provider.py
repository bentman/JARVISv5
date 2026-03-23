from pathlib import Path

import pytest

from backend.voice.tts_provider import PiperTTSProvider


def test_tts_provider_synthesize_to_file_returns_output_path(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "voice.onnx"
    config_path = tmp_path / "voice.onnx.json"
    output_path = tmp_path / "out" / "speech.wav"
    model_path.write_text("model", encoding="utf-8")
    config_path.write_text("config", encoding="utf-8")

    class _Voice:
        def synthesize(self, text: str, wav_file) -> None:
            _ = wav_file
            assert text == "hello world"

    class _VoiceClass:
        @staticmethod
        def load(model_path: str, config_path: str):
            assert Path(model_path).name == "voice.onnx"
            assert Path(config_path).name == "voice.onnx.json"
            return _Voice()

    class _DummyWaveFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type
            _ = exc
            _ = tb
            return False

    monkeypatch.setattr("backend.voice.tts_provider.wave.open", lambda *_args, **_kwargs: _DummyWaveFile())

    monkeypatch.setattr("backend.voice.tts_provider._load_piper_voice_class", lambda: _VoiceClass)

    provider = PiperTTSProvider(model_path=str(model_path), config_path=str(config_path))
    result = provider.synthesize_to_file("hello world", str(output_path))

    assert result == str(output_path)


def test_tts_provider_synthesize_to_file_requires_text(tmp_path) -> None:
    provider = PiperTTSProvider(
        model_path=str(tmp_path / "voice.onnx"),
        config_path=str(tmp_path / "voice.onnx.json"),
    )

    with pytest.raises(RuntimeError, match="tts_text_required"):
        provider.synthesize_to_file("   ", str(tmp_path / "speech.wav"))


def test_tts_provider_synthesize_to_file_handles_missing_dependency(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "voice.onnx"
    config_path = tmp_path / "voice.onnx.json"
    model_path.write_text("model", encoding="utf-8")
    config_path.write_text("config", encoding="utf-8")

    def _raise_import_error():
        raise ImportError("missing piper")

    monkeypatch.setattr("backend.voice.tts_provider._load_piper_voice_class", _raise_import_error)

    provider = PiperTTSProvider(model_path=str(model_path), config_path=str(config_path))

    with pytest.raises(RuntimeError, match="piper_dependency_unavailable"):
        provider.synthesize_to_file("hello", str(tmp_path / "speech.wav"))
