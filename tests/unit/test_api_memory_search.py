import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.memory.memory_manager import MemoryManager


client = TestClient(app)


class _TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def _build_real_memory(tmp_dir: str) -> MemoryManager:
    base = Path(tmp_dir)
    return MemoryManager(
        episodic_db_path=str(base / "episodic.db"),
        working_base_path=str(base / "working"),
        working_archive_path=str(base / "archives"),
        semantic_db_path=str(base / "semantic.db"),
        embedding_model=_TestEmbeddingFunction(),
    )


def test_memory_search_returns_semantic_and_episodic_results(monkeypatch) -> None:
    class _SemanticStub:
        def search_text(self, query: str, top_k: int = 5):
            assert query == "alpha"
            assert top_k == 3
            return [
                {
                    "id": 101,
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
    assert semantic["metadata"]["id"] == 101
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


def test_delete_semantic_memory_returns_200_when_found(monkeypatch) -> None:
    class _MemoryStub:
        def delete_knowledge(self, entry_id: int) -> bool:
            assert int(entry_id) == 1
            return True

    monkeypatch.setattr("backend.api.main._build_memory_manager", lambda _settings: _MemoryStub())

    response = client.delete("/memory/semantic/1")
    assert response.status_code == 200
    assert response.json() == {"deleted": True, "entry_id": 1}


def test_delete_semantic_memory_returns_404_when_not_found(monkeypatch) -> None:
    class _MemoryStub:
        def delete_knowledge(self, entry_id: int) -> bool:
            assert int(entry_id) == 999
            return False

    monkeypatch.setattr("backend.api.main._build_memory_manager", lambda _settings: _MemoryStub())

    response = client.delete("/memory/semantic/999")
    assert response.status_code == 404
    assert response.json().get("detail") == "memory_entry_not_found"


def test_memory_search_delete_flow_exposes_metadata_id_and_preserves_non_deleted_entry(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        memory = _build_real_memory(tmp_dir)

        keep_id = memory.store_knowledge(
            "semantic keep entry about deterministic testing",
            {"source": "unit-test", "label": "keep"},
        )
        delete_id = memory.store_knowledge(
            "semantic delete entry about deterministic testing",
            {"source": "unit-test", "label": "delete"},
        )

        monkeypatch.setattr("backend.api.main._build_memory_manager", lambda _settings: memory)

        before_delete = client.get(
            "/memory/search",
            params={"q": "semantic delete entry about deterministic testing", "limit": 10},
        )
        assert before_delete.status_code == 200
        semantic_before = before_delete.json().get("semantic_results", [])
        assert semantic_before
        assert all("id" in item.get("metadata", {}) for item in semantic_before)
        assert any(int(item["metadata"]["id"]) == int(delete_id) for item in semantic_before)

        delete_response = client.delete(f"/memory/semantic/{delete_id}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"deleted": True, "entry_id": int(delete_id)}

        after_delete = client.get(
            "/memory/search",
            params={"q": "semantic delete entry about deterministic testing", "limit": 10},
        )
        assert after_delete.status_code == 200
        semantic_after = after_delete.json().get("semantic_results", [])
        assert all(int(item.get("metadata", {}).get("id", -1)) != int(delete_id) for item in semantic_after)

        keep_search = client.get(
            "/memory/search",
            params={"q": "semantic keep entry about deterministic testing", "limit": 10},
        )
        assert keep_search.status_code == 200
        semantic_keep = keep_search.json().get("semantic_results", [])
        assert any(int(item.get("metadata", {}).get("id", -1)) == int(keep_id) for item in semantic_keep)
