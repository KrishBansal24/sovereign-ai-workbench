"""Persistent, local FAISS-backed vector retrieval for RAG chunks.

Raw vectors and metadata are retained beside a normalized FAISS index so the
application can recreate its in-memory search index after a process restart.
"""

import json
from pathlib import Path
from typing import TypedDict, cast

import faiss
import numpy as np

from app.core.config import settings


class ChunkMetadata(TypedDict, total=False):
    """Traceability fields stored for each embedded source chunk."""

    document_id: str
    filename: str
    chunk_id: str
    chunk_index: int
    text: str
    character_count: int


class VectorStoreService:
    """Persist chunk vectors locally and rank them by cosine similarity."""

    def __init__(self, directory: Path | None = None) -> None:
        """Open a local vector-store directory, creating it when necessary.

        Args:
            directory: Optional storage location, primarily useful for tests.
                The configured knowledge-data directory is used by default.
        """
        self.directory = directory or settings.data_directory / "knowledge"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.vectors_file = self.directory / "vectors.npy"
        self.metadata_file = self.directory / "metadata.json"
        self.index_file = self.directory / "index.faiss"
        self.vectors = np.load(self.vectors_file) if self.vectors_file.exists() else np.empty((0, 0), dtype="float32")
        self.metadata: list[ChunkMetadata] = (
            cast(list[ChunkMetadata], json.loads(self.metadata_file.read_text()))
            if self.metadata_file.exists()
            else []
        )

    def replace_document(
        self,
        document_id: str,
        vectors: list[list[float]],
        metadata: list[ChunkMetadata],
    ) -> None:
        """Replace all indexed chunks for a document and persist the result.

        Args:
            document_id: ID whose previous chunk vectors should be removed.
            vectors: Same-ordered embedding vectors for the replacement chunks.
            metadata: Same-ordered source metadata used to explain retrieval.
        """
        kept_indices = [
            index
            for index, item in enumerate(self.metadata)
            if item["document_id"] != document_id
        ]
        retained_vectors = (
            self.vectors[kept_indices]
            if kept_indices
            else np.empty((0, len(vectors[0])), dtype="float32")
        )
        replacement_vectors = np.asarray(vectors, dtype="float32")
        self.vectors = (
            np.vstack((retained_vectors, replacement_vectors))
            if retained_vectors.size
            else replacement_vectors
        )
        self.metadata = [self.metadata[index] for index in kept_indices] + metadata
        self._save()

    def remove_document(self, document_id: str) -> bool:
        """Remove all stored vectors and traceability records for one document.

        Returns:
            ``True`` only when indexed chunks existed for the supplied ID.
        """
        if not any(item["document_id"] == document_id for item in self.metadata):
            return False
        kept_indices = [
            index
            for index, item in enumerate(self.metadata)
            if item["document_id"] != document_id
        ]
        self.vectors = self.vectors[kept_indices] if kept_indices else np.empty((0, 0), dtype="float32")
        self.metadata = [self.metadata[index] for index in kept_indices]
        self._save()
        return True

    def search(self, vector: list[float], top_k: int) -> list[tuple[ChunkMetadata, float]]:
        """Return the highest-scoring locally indexed chunks for one query vector.

        Both document and query vectors are L2-normalized before FAISS
        ``IndexFlatIP`` search. Its inner-product score therefore represents
        cosine similarity for non-zero vectors.
        """
        if not self.metadata:
            return []
        matrix = self._normalize(self.vectors.copy())
        query = self._normalize(np.asarray([vector], dtype="float32"))
        index = faiss.IndexFlatIP(matrix.shape[1]); index.add(matrix)
        scores, ids = index.search(query, min(top_k, len(self.metadata)))
        return [(self.metadata[i], float(score)) for score, i in zip(scores[0], ids[0]) if i >= 0]

    def documents(self) -> list[dict[str, str]]:
        """List unique indexed documents with their original filenames."""
        seen: dict[str, dict[str, str]] = {}
        for item in self.metadata:
            seen[item["document_id"]] = {
                "document_id": item["document_id"],
                "filename": item["filename"],
            }
        return list(seen.values())

    def _save(self) -> None:
        """Persist raw vectors, metadata, and a normalized FAISS sidecar index."""
        np.save(self.vectors_file, self.vectors)
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        if self.vectors.size:
            # Persist the same normalized inner-product index used for cosine
            # retrieval. Startup reloads raw vectors and rebuilds search state.
            index = faiss.IndexFlatIP(self.vectors.shape[1])
            index.add(self._normalize(self.vectors.copy()))
            faiss.write_index(index, str(self.index_file))
        elif self.index_file.exists():
            self.index_file.unlink()

    @staticmethod
    def _normalize(values: np.ndarray) -> np.ndarray:
        """L2-normalize vector rows while leaving zero vectors stable."""
        norms = np.linalg.norm(values, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return values / norms


vector_store = VectorStoreService()
