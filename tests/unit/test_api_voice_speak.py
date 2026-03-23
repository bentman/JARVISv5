from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_voice_speak_returns_audio_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _speak(self, text: str):
        assert text == "hello voice"
        return {
            "audio_path": "data/voice/tts-abc.wav",
            "model_id": "piper-tts",
            "profile": "light",
            "hardware": "CPU_ONLY",
        }

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.speak", _speak)

    response = client.post("/voice/speak", json={"text": "hello voice"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["audio_path"] == "data/voice/tts-abc.wav"
    assert payload["model_id"] == "piper-tts"
    assert payload["profile"] == "light"
    assert payload["hardware"] == "CPU_ONLY"


def test_voice_speak_returns_503_when_tts_unavailable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _speak(self, text: str):
        _ = text
        raise RuntimeError("tts_model_not_available")

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.speak", _speak)

    response = client.post("/voice/speak", json={"text": "hello voice"})

    assert response.status_code == 503
    assert response.json().get("detail") == "tts_model_not_available"
