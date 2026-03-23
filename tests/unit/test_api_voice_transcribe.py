from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_voice_transcribe_returns_transcript_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _transcribe(self, audio_path: str):
        assert audio_path == "tests/fixtures/sample.wav"
        return {
            "transcript": "hello world",
            "model_id": "whisper-base",
            "profile": "light",
            "hardware": "CPU_ONLY",
        }

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.transcribe", _transcribe)

    response = client.post("/voice/transcribe", json={"audio_path": "tests/fixtures/sample.wav"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "hello world"
    assert payload["model_id"] == "whisper-base"
    assert payload["profile"] == "light"
    assert payload["hardware"] == "CPU_ONLY"


def test_voice_transcribe_returns_503_when_stt_unavailable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _transcribe(self, audio_path: str):
        _ = audio_path
        raise RuntimeError("stt_model_not_available")

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.transcribe", _transcribe)

    response = client.post("/voice/transcribe", json={"audio_path": "tests/fixtures/sample.wav"})

    assert response.status_code == 503
    assert response.json().get("detail") == "stt_unavailable"
