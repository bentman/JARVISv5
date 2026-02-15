import json
import os
import sqlite3
from contextlib import closing
from typing import Any

import faiss
import numpy as np


class SemanticMemory:
    def __init__(
        self,
        db_path: str = "data/semantic/metadata.db",
        embedding_model: Any = None,
    ) -> None:
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            self.embedding_model = embedding_model

        self._init_db()
        self.index: faiss.IndexFlatL2 | None = None
        self.dimension: int | None = None
        self._rebuild_index_from_db()

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
            return int(cursor.lastrowid)

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
