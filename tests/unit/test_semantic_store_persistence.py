import tempfile
from pathlib import Path

import faiss

from backend.memory.semantic_store import SemanticMemory


class TestEmbeddingFunction:
    def encode(self, text: str) -> list[float]:
        base = float((sum(ord(ch) for ch in text) % 13) + 1)
        return [base] * 384


def test_existing_index_loads_without_rebuild(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "data" / "semantic" / "metadata.db"
        index_path = base / "data" / "semantic" / "index.faiss"

        memory = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )
        memory.add_text("alpha memory", {"source": "seed"})
        assert index_path.exists()

        def _rebuild_should_not_run(self) -> None:  # pragma: no cover - assertion helper
            raise AssertionError("rebuild should not run when valid index file exists")

        monkeypatch.setattr(SemanticMemory, "_rebuild_index_from_db", _rebuild_should_not_run)

        loaded = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )
        results = loaded.search("alpha", k=1)
        assert results


def test_missing_index_rebuilds_and_writes_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "data" / "semantic" / "metadata.db"
        index_path = base / "data" / "semantic" / "index.faiss"

        memory = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )
        memory.add_text("beta memory", {"source": "seed"})
        assert index_path.exists()

        index_path.unlink()
        assert not index_path.exists()

        rebuilt = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )

        assert index_path.exists()
        assert rebuilt.search("beta", k=1)


def test_corrupt_index_rebuilds_and_overwrites_file() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "data" / "semantic" / "metadata.db"
        index_path = base / "data" / "semantic" / "index.faiss"

        memory = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )
        memory.add_text("gamma memory", {"source": "seed"})
        assert index_path.exists()

        index_path.write_bytes(b"corrupt-index")

        recovered = SemanticMemory(
            db_path=str(db_path),
            index_path=str(index_path),
            embedding_model=TestEmbeddingFunction(),
        )

        assert recovered.search("gamma", k=1)

        loaded_index = faiss.read_index(str(index_path))
        assert loaded_index.ntotal >= 1


def test_default_index_path_and_db_path_derived_override() -> None:
    default_index = SemanticMemory._derive_index_path("data/semantic/metadata.db")
    assert default_index.replace("\\", "/") == "data/semantic/index.faiss"

    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        db_path = base / "custom_data" / "semantic" / "metadata.db"
        expected_index = base / "custom_data" / "semantic" / "index.faiss"

        memory = SemanticMemory(
            db_path=str(db_path),
            embedding_model=TestEmbeddingFunction(),
        )

        assert Path(memory.index_path) == expected_index
