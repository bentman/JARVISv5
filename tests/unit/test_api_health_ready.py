from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_health_ready_returns_ready_true() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["service"] == "JARVISv5-backend"
    assert body["detail"] == "ready"


def test_health_ready_returns_503_when_memory_manager_unavailable(monkeypatch) -> None:
    def _raise_build(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("backend.api.main._build_memory_manager", _raise_build)

    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert "detail" in body
    assert body["detail"]["ready"] is False
    assert body["detail"]["service"] == "JARVISv5-backend"
    assert body["detail"]["detail"] == "readiness_unavailable"
