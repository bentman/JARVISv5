from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_post_task_returns_required_keys(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    response = client.post("/task", json={"user_input": "hello"})

    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert "final_state" in body
    assert "llm_output" in body


def test_get_task_non_existent_returns_404(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    response = client.get("/task/does-not-exist")

    assert response.status_code == 404
