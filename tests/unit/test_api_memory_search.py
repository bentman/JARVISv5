from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_memory_search_returns_semantic_and_episodic_results(monkeypatch) -> None:
    class _SemanticStub:
        def search_text(self, query: str, top_k: int = 5):
            assert query == "alpha"
            assert top_k == 3
            return [
                {
                    "text": "semantic hit",
                    "metadata": {"doc_id": "doc-1"},
                    "vector_id": 7,
                    "distance": 0.125,
                    "similarity_score": 0.889,
                }
            ]

    class _EpisodicStub:
        def search_decisions(self, query: str, limit: int = 20, task_id: str | None = None):
            assert query == "alpha"
            assert limit == 3
            assert task_id is None
            return [
                {
                    "id": 11,
                    "timestamp": "2026-03-07T00:00:00",
                    "task_id": "task-1",
                    "action_type": "plan",
                    "content": "episodic hit",
                    "status": "ok",
                }
            ]

    class _MemoryStub:
        def __init__(self) -> None:
            self.semantic = _SemanticStub()
            self.episodic = _EpisodicStub()

    monkeypatch.setattr("backend.api.main._build_memory_manager", lambda _settings: _MemoryStub())

    response = client.get("/memory/search", params={"q": "alpha", "limit": 3})
    assert response.status_code == 200
    body = response.json()

    assert body["query"] == "alpha"
    assert len(body["semantic_results"]) == 1
    assert len(body["episodic_results"]) == 1

    semantic = body["semantic_results"][0]
    assert semantic["source"] == "semantic"
    assert semantic["content"] == "semantic hit"
    assert semantic["score"] == 0.889
    assert semantic["metadata"]["doc_id"] == "doc-1"
    assert semantic["metadata"]["vector_id"] == 7
    assert semantic["metadata"]["distance"] == 0.125

    episodic = body["episodic_results"][0]
    assert episodic["source"] == "episodic"
    assert episodic["content"] == "episodic hit"
    assert episodic["score"] is None
    assert episodic["metadata"]["id"] == 11
    assert episodic["metadata"]["task_id"] == "task-1"


def test_memory_search_rejects_empty_query() -> None:
    response = client.get("/memory/search", params={"q": "   "})
    assert response.status_code == 422
    assert response.json().get("detail") == "query_required"


def test_memory_search_returns_empty_lists_when_no_results(monkeypatch) -> None:
    class _SemanticStub:
        def search_text(self, query: str, top_k: int = 5):
            return []

    class _EpisodicStub:
        def search_decisions(self, query: str, limit: int = 20, task_id: str | None = None):
            return []

    class _MemoryStub:
        def __init__(self) -> None:
            self.semantic = _SemanticStub()
            self.episodic = _EpisodicStub()

    monkeypatch.setattr("backend.api.main._build_memory_manager", lambda _settings: _MemoryStub())

    response = client.get("/memory/search", params={"q": "none"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "none"
    assert body["semantic_results"] == []
    assert body["episodic_results"] == []
