from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_task_stream_returns_chunk_and_done_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _run(self, user_input: str, task_id: str | None = None, **kwargs):
        return {
            "task_id": task_id or "task-stream-1",
            "final_state": "ARCHIVE",
            "context": {
                "llm_output": "Hello from stream",
                "llm_stream_chunks": ["Hello from stream"],
                "tool_ok": True,
            },
        }

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _run)

    response = client.post("/task/stream", json={"user_input": "hello"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "event: chunk" in body
    assert 'data: {"chunk":"Hello from stream"}' in body
    assert "event: done" in body
    assert '"task_id":"task-stream-1"' in body
    assert '"final_state":"ARCHIVE"' in body


def test_task_stream_returns_404_for_missing_task_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    response = client.post(
        "/task/stream",
        json={"task_id": "does-not-exist", "user_input": "hello"},
    )

    assert response.status_code == 404
    assert response.json().get("detail") == "Task not found"


def test_task_stream_emits_error_event_when_service_raises(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    def _run(self, user_input: str, task_id: str | None = None, **kwargs):
        raise RuntimeError("stream exploded")

    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _run)

    response = client.post("/task/stream", json={"user_input": "hello"})

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert "event: error" in body
    assert 'data: {"error":"stream exploded"}' in body
