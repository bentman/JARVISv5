import json

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_workflow_telemetry_returns_404_when_task_not_found(monkeypatch) -> None:
    def _get_task_state(self, task_id: str):
        return None

    monkeypatch.setattr("backend.memory.memory_manager.MemoryManager.get_task_state", _get_task_state)

    response = client.get("/workflow/task-missing")
    assert response.status_code == 404
    assert response.json().get("detail") == "Task not found"


def test_workflow_telemetry_returns_defaults_when_no_telemetry(monkeypatch) -> None:
    def _get_task_state(self, task_id: str):
        return {"task_id": task_id, "status": "INIT"}

    def _search_decisions(self, query: str, limit: int = 20, task_id: str | None = None):
        return []

    monkeypatch.setattr("backend.memory.memory_manager.MemoryManager.get_task_state", _get_task_state)
    monkeypatch.setattr("backend.memory.episodic_db.EpisodicMemory.search_decisions", _search_decisions)

    response = client.get("/workflow/task-1")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-1"
    assert body["workflow_graph"] == {}
    assert body["workflow_execution_order"] == []
    assert body["node_events"] == []


def test_workflow_telemetry_returns_schema_aligned_payload(monkeypatch) -> None:
    def _get_task_state(self, task_id: str):
        return {
            "task_id": task_id,
            "workflow_graph": {
                "nodes": ["router", "llm_worker"],
                "edges": [{"from_node": "router", "to_node": "llm_worker"}],
                "entry": "router",
            },
            "workflow_execution_order": ["router", "llm_worker"],
        }

    valid_payload = {
        "node_id": "router",
        "node_type": "RouterNode",
        "controller_state": "EXECUTE",
        "event_type": "node_start",
        "success": True,
        "task_id": "task-2",
        "elapsed_ns": 123,
        "start_offset_ns": 10,
        "error": None,
    }

    def _search_decisions(self, query: str, limit: int = 20, task_id: str | None = None):
        return [
            {"id": 2, "action_type": "dag_node_event", "content": "{not json}"},
            {"id": 1, "action_type": "dag_node_event", "content": json.dumps(valid_payload)},
        ]

    monkeypatch.setattr("backend.memory.memory_manager.MemoryManager.get_task_state", _get_task_state)
    monkeypatch.setattr("backend.memory.episodic_db.EpisodicMemory.search_decisions", _search_decisions)

    response = client.get("/workflow/task-2")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "task-2"
    assert body["workflow_graph"]["entry"] == "router"
    assert body["workflow_execution_order"] == ["router", "llm_worker"]
    assert len(body["node_events"]) == 1
    event = body["node_events"][0]
    assert event["node_id"] == "router"
    assert event["event_type"] == "node_start"
    assert event["start_offset_ns"] == 10
