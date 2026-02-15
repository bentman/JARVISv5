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
