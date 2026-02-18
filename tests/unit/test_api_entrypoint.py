from fastapi.testclient import TestClient
import sys
import types

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


def test_post_task_with_task_id_continues_existing_task(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    class _StubLlama:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def create_completion(
            self,
            prompt: str,
            max_tokens: int = 100,
            echo: bool = False,
            stop: list[str] | None = None,
        ) -> dict:
            if "What is my name? Reply with only the name." in prompt:
                return {"choices": [{"text": "Alice"}]}
            return {"choices": [{"text": "Acknowledged."}]}

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=_StubLlama))

    first = client.post("/task", json={"user_input": "My name is Alice. Remember it."})
    assert first.status_code == 200
    first_body = first.json()
    task_id = str(first_body["task_id"])

    second = client.post(
        "/task",
        json={"task_id": task_id, "user_input": "What is my name? Reply with only the name."},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["task_id"] == task_id
    llm_output = str(second_body.get("llm_output", "")).strip()
    assert llm_output == "Alice"
    lowered = llm_output.lower()
    assert "username" not in lowered
    assert "password" not in lowered

    state_response = client.get(f"/task/{task_id}")
    assert state_response.status_code == 200
    state = state_response.json()
    messages = state.get("messages", [])
    assert isinstance(messages, list)
    contents = [str(item.get("content", "")) for item in messages if isinstance(item, dict)]
    assert any("My name is Alice. Remember it." in content for content in contents)
    assert any("What is my name?" in content for content in contents)
