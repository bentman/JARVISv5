from io import BytesIO

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def _mock_run(self, user_input: str, task_id: str | None = None, **kwargs):
    return {
        "task_id": task_id or "task-upload-1",
        "final_state": "ARCHIVE",
        "context": {
            "llm_output": f"processed::{user_input[:64]}",
            "tool_ok": True,
        },
    }


def test_task_upload_txt_success(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _mock_run)

    response = client.post(
        "/task/upload",
        data={"user_input": "summarize this"},
        files={"file": ("note.txt", BytesIO(b"hello from text file"), "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-upload-1"
    assert body["final_state"] == "ARCHIVE"
    attachment = body.get("attachment")
    assert isinstance(attachment, dict)
    assert attachment.get("filename") == "note.txt"
    assert attachment.get("mime_type") == "text/plain"
    assert int(attachment.get("extracted_text_length", 0)) > 0


def test_task_upload_md_success(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _mock_run)

    response = client.post(
        "/task/upload",
        data={"user_input": "use markdown"},
        files={"file": ("context.md", BytesIO(b"# Header\nBody"), "text/markdown")},
    )

    assert response.status_code == 200
    body = response.json()
    attachment = body.get("attachment")
    assert isinstance(attachment, dict)
    assert attachment.get("filename") == "context.md"
    assert attachment.get("mime_type") == "text/markdown"
    assert int(attachment.get("extracted_text_length", 0)) > 0


def test_task_upload_unsupported_extension_returns_415(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _mock_run)

    response = client.post(
        "/task/upload",
        data={"user_input": "reject this"},
        files={"file": ("bad.csv", BytesIO(b"a,b,c"), "text/csv")},
    )

    assert response.status_code == 415
    detail = response.json().get("detail", {})
    assert detail.get("code") == "unsupported_file_type"


def test_task_json_submit_still_supported(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    monkeypatch.setattr("backend.controller.controller_service.ControllerService.run", _mock_run)

    response = client.post(
        "/task",
        json={"user_input": "json submit remains"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body.get("task_id") == "task-upload-1"
    assert body.get("final_state") == "ARCHIVE"
    assert isinstance(body.get("llm_output"), str)
