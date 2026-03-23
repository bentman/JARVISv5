import pytest

from backend.voice.stt_provider import FasterWhisperSTTProvider


class _Segment:
    def __init__(self, text: str) -> None:
        self.text = text


def test_stt_provider_transcribe_file_returns_joined_text(monkeypatch) -> None:
    class _Model:
        def __init__(self, model_dir: str) -> None:
            self.model_dir = model_dir

        def transcribe(self, audio_path: str):
            assert self.model_dir == "models/faster-whisper-base"
            assert audio_path == "tests/fixtures/sample.wav"
            return [
                _Segment("hello"),
                _Segment("world"),
            ], {"language": "en"}

    monkeypatch.setattr("backend.voice.stt_provider._load_whisper_model_class", lambda: _Model)

    provider = FasterWhisperSTTProvider(model_dir="models/faster-whisper-base")
    transcript = provider.transcribe_file("tests/fixtures/sample.wav")

    assert transcript == "hello world"


def test_stt_provider_transcribe_file_requires_audio_path() -> None:
    provider = FasterWhisperSTTProvider(model_dir="models/faster-whisper-base")

    with pytest.raises(RuntimeError, match="audio_path_required"):
        provider.transcribe_file("   ")


def test_stt_provider_transcribe_file_handles_missing_dependency(monkeypatch) -> None:
    def _raise_import_error():
        raise ImportError("missing faster_whisper")

    monkeypatch.setattr("backend.voice.stt_provider._load_whisper_model_class", _raise_import_error)

    provider = FasterWhisperSTTProvider(model_dir="models/faster-whisper-base")

    with pytest.raises(RuntimeError, match="faster_whisper_dependency_unavailable"):
        provider.transcribe_file("tests/fixtures/sample.wav")
