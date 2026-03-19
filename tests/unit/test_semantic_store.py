import tempfile
from pathlib import Path

from backend.memory.semantic_store import SemanticMemory


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def test_add_text_stores_in_faiss_and_sqlite() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        record_id = memory.add_text("hello world", {"source": "unit-test"})
        assert record_id > 0
        assert memory.index is not None
        assert memory.index.ntotal == 1


def test_search_returns_expected_text() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        memory.add_text("alpha context", {"tag": "alpha"})
        memory.add_text("beta context", {"tag": "beta"})

        results = memory.search("alpha query", k=2)
        assert results
        first = results[0]
        assert "text" in first
        assert "metadata" in first
        assert "score" in first


def test_delete_existing_entry_returns_true() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        entry_id = memory.add_text("delete me", {"tag": "delete"})
        deleted = memory.delete(entry_id)

        assert deleted is True
        results = memory.search_text("delete me", top_k=5)
        assert all(int(item.get("id", -1)) != int(entry_id) for item in results)


def test_delete_nonexistent_entry_returns_false() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        memory.add_text("existing", {"tag": "keep"})
        deleted = memory.delete(999999)
        assert deleted is False


def test_index_rebuilt_after_delete_keeps_remaining_entry_retrievable() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        delete_id = memory.add_text("drop this entry", {"tag": "drop"})
        keep_id = memory.add_text("keep this entry", {"tag": "keep"})

        assert memory.delete(delete_id) is True

        results = memory.search_text("keep this entry", top_k=5)
        assert results
        kept = [item for item in results if int(item.get("id", -1)) == int(keep_id)]
        assert kept
        assert isinstance(kept[0].get("similarity_score"), float)


def test_search_text_returns_id_field() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "metadata.db"
        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        entry_id = memory.add_text("id field check", {"source": "unit-test"})
        results = memory.search_text("id field check", top_k=1)

        assert results
        first = results[0]
        assert "id" in first
        assert int(first["id"]) == int(entry_id)
