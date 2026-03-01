import json
import os
import sqlite3
from contextlib import closing
from math import isfinite
from typing import Any

import faiss
import numpy as np


def _l2_distance_to_similarity(distance: float) -> float:
    """Convert L2 distance to normalized similarity score in [0, 1]."""
    distance_f = float(distance)
    if not isfinite(distance_f):
        return 0.0
    if distance_f < 0.0:
        distance_f = 0.0
    similarity = 1.0 / (1.0 + distance_f)
    if similarity < 0.0:
        return 0.0
    if similarity > 1.0:
        return 1.0
    return similarity


class SemanticMemory:
    def __init__(
        self,
        db_path: str = "data/semantic/metadata.db",
        embedding_model: Any = None,
        index_path: str | None = None,
    ) -> None:
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.index_path = index_path or self._derive_index_path(self.db_path)
        index_dir = os.path.dirname(self.index_path)
        if index_dir:
            os.makedirs(index_dir, exist_ok=True)

        if embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.embedding_model = embedding_model

        self._init_db()
        self.index: faiss.IndexFlatL2 | None = None
        self.dimension: int | None = None
        self.embedding_dimension = self._probe_embedding_dimension()
        if not self._load_index_from_file():
            self._rebuild_index_from_db()
            self._persist_index_best_effort()

    @staticmethod
    def _derive_index_path(db_path: str) -> str:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            return os.path.join(db_dir, "index.faiss")
        return "index.faiss"

    def _probe_embedding_dimension(self) -> int:
        probe_vector = self._embed("dimension-probe")
        return len(probe_vector)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    vector_id INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def _embed(self, text: str) -> list[float]:
        vector = self.embedding_model.encode(text)
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        if isinstance(vector, list) and vector and isinstance(vector[0], list):
            vector = vector[0]
        return [float(v) for v in vector]

    def _ensure_index(self, dimension: int) -> None:
        if self.index is None:
            self.index = faiss.IndexFlatL2(dimension)
            self.dimension = dimension
            return

        if self.dimension != dimension:
            raise ValueError("Embedding dimension mismatch")

    def _to_faiss_array(self, vector: list[float]) -> np.ndarray:
        return np.asarray([vector], dtype="float32")

    def _rebuild_index_from_db(self) -> None:
        self.index = None
        self.dimension = None
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT text, vector_id FROM embeddings ORDER BY vector_id ASC"
            ).fetchall()

        if not rows:
            return

        for row in rows:
            vector = self._embed(row[0])
            self._ensure_index(len(vector))
            assert self.index is not None
            self.index.add(self._to_faiss_array(vector))

    def _load_index_from_file(self) -> bool:
        if not os.path.exists(self.index_path):
            return False

        try:
            loaded_index = faiss.read_index(self.index_path)
        except Exception as exc:
            print(f"[WARN] Failed to read FAISS index '{self.index_path}': {exc}")
            return False

        if not self._is_valid_loaded_index(loaded_index):
            return False

        self.index = loaded_index
        self.dimension = int(getattr(loaded_index, "d"))
        return True

    def _is_valid_loaded_index(self, index: Any) -> bool:
        index_d = getattr(index, "d", None)
        if not isinstance(index_d, int) or index_d <= 0:
            print("[WARN] Loaded FAISS index missing valid dimension; rebuilding")
            return False

        index_metric_type = getattr(index, "metric_type", None)
        if index_metric_type != faiss.METRIC_L2:
            print("[WARN] Loaded FAISS index metric is not L2; rebuilding")
            return False

        if index_d != self.embedding_dimension:
            print(
                "[WARN] Loaded FAISS index dimension mismatch "
                f"(index={index_d}, embedding={self.embedding_dimension}); rebuilding"
            )
            return False

        return True

    def _persist_index_best_effort(self) -> None:
        if self.index is None:
            return

        try:
            faiss.write_index(self.index, self.index_path)
        except Exception as exc:
            print(f"[WARN] Failed to persist FAISS index '{self.index_path}': {exc}")

    def add_text(self, text: str, metadata_dict: dict[str, Any]) -> int:
        vector = self._embed(text)
        self._ensure_index(len(vector))
        assert self.index is not None

        vector_id = self.index.ntotal
        self.index.add(self._to_faiss_array(vector))

        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO embeddings (text, metadata, vector_id) VALUES (?, ?, ?)",
                (text, json.dumps(metadata_dict), int(vector_id)),
            )
            conn.commit()
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert embedding metadata")
            inserted_id = int(cursor.lastrowid)

        self._persist_index_best_effort()
        return inserted_id

    def search(self, query_text: str, k: int = 5) -> list[dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = self._embed(query_text)
        distances, indices = self.index.search(
            self._to_faiss_array(query_vector),
            k,
        )

        results: list[dict[str, Any]] = []
        with closing(self._connect()) as conn:
            for score, vector_id in zip(distances[0], indices[0]):
                if int(vector_id) < 0:
                    continue
                row = conn.execute(
                    "SELECT text, metadata FROM embeddings WHERE vector_id = ?",
                    (int(vector_id),),
                ).fetchone()
                if row is None:
                    continue
                results.append(
                    {
                        "text": row[0],
                        "metadata": json.loads(row[1]),
                        "score": float(score),
                    }
                )
        return results

    def search_text(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = self._embed(query)
        distances, indices = self.index.search(
            self._to_faiss_array(query_vector),
            top_k,
        )

        results: list[dict[str, Any]] = []
        with closing(self._connect()) as conn:
            for distance, vector_id in zip(distances[0], indices[0]):
                vector_id_int = int(vector_id)
                if vector_id_int < 0:
                    continue

                row = conn.execute(
                    "SELECT text, metadata FROM embeddings WHERE vector_id = ?",
                    (vector_id_int,),
                ).fetchone()
                if row is None:
                    continue

                distance_f = float(distance)
                similarity_score = _l2_distance_to_similarity(distance_f)

                results.append(
                    {
                        "text": row[0],
                        "metadata": json.loads(row[1]),
                        "vector_id": vector_id_int,
                        "distance": distance_f,
                        "similarity_score": similarity_score,
                    }
                )

        results.sort(
            key=lambda item: (
                -float(item["similarity_score"]),
                int(item["vector_id"]),
            )
        )
        return results
