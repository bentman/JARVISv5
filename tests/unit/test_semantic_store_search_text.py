import tempfile
from pathlib import Path

from backend.memory.semantic_store import SemanticMemory, _l2_distance_to_similarity


class DeterministicEmbeddingModel:
    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def encode(self, text: str) -> list[float]:
        if text not in self._mapping:
            raise KeyError(f"Missing embedding mapping for: {text}")
        return self._mapping[text]


def test_l2_distance_to_similarity_exact_conversion() -> None:
    assert _l2_distance_to_similarity(0.0) == 1.0
    assert _l2_distance_to_similarity(1.0) == 0.5
    assert _l2_distance_to_similarity(3.0) == 0.25


def test_search_text_empty_index_returns_empty_list() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "data" / "semantic" / "metadata.db"
        model = DeterministicEmbeddingModel({"dimension-probe": [0.0, 0.0], "query": [0.0, 0.0]})
        memory = SemanticMemory(db_path=str(db_path), embedding_model=model)

        assert memory.search_text("query", top_k=5) == []


def test_search_text_returns_similarity_in_range_and_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "data" / "semantic" / "metadata.db"
        model = DeterministicEmbeddingModel(
            {
                "dimension-probe": [0.0, 0.0],
                "query": [0.0, 0.0],
                "doc-a": [0.0, 0.0],
                "doc-b": [1.0, 0.0],
            }
        )
        memory = SemanticMemory(db_path=str(db_path), embedding_model=model)

        memory.add_text("doc-a", {"task_id": "task-a"})
        memory.add_text("doc-b", {"task_id": "task-b"})

        results = memory.search_text("query", top_k=2)
        assert len(results) == 2

        for item in results:
            assert "text" in item
            assert "metadata" in item
            assert "vector_id" in item
            assert "distance" in item
            assert "similarity_score" in item
            assert 0.0 <= float(item["similarity_score"]) <= 1.0


def test_search_text_orders_by_similarity_desc_then_vector_id() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "data" / "semantic" / "metadata.db"
        model = DeterministicEmbeddingModel(
            {
                "dimension-probe": [0.0, 0.0],
                "query": [0.0, 0.0],
                "doc-first-tie": [1.0, 0.0],
                "doc-second-tie": [-1.0, 0.0],
                "doc-best": [0.0, 0.0],
            }
        )
        memory = SemanticMemory(db_path=str(db_path), embedding_model=model)

        memory.add_text("doc-first-tie", {"tag": "first"})  # vector_id=0, dist=1.0
        memory.add_text("doc-second-tie", {"tag": "second"})  # vector_id=1, dist=1.0
        memory.add_text("doc-best", {"tag": "best"})  # vector_id=2, dist=0.0

        results = memory.search_text("query", top_k=3)

        assert [item["text"] for item in results] == ["doc-best", "doc-first-tie", "doc-second-tie"]
        assert results[0]["distance"] == 0.0
        assert results[0]["similarity_score"] == 1.0
        assert results[1]["distance"] == 1.0
        assert results[1]["similarity_score"] == 0.5
        assert results[2]["distance"] == 1.0
        assert results[2]["similarity_score"] == 0.5
