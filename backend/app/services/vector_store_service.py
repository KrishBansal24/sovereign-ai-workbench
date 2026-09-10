import json
from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings


class VectorStoreService:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or settings.data_directory / "knowledge"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.vectors_file, self.metadata_file, self.index_file = self.directory / "vectors.npy", self.directory / "metadata.json", self.directory / "index.faiss"
        self.vectors = np.load(self.vectors_file) if self.vectors_file.exists() else np.empty((0, 0), dtype="float32")
        self.metadata = json.loads(self.metadata_file.read_text()) if self.metadata_file.exists() else []

    def replace_document(self, document_id: str, vectors: list[list[float]], metadata: list[dict]) -> None:
        keep = [i for i, item in enumerate(self.metadata) if item["document_id"] != document_id]
        old = self.vectors[keep] if len(keep) else np.empty((0, len(vectors[0])), dtype="float32")
        new = np.asarray(vectors, dtype="float32")
        self.vectors = np.vstack((old, new)) if old.size else new
        self.metadata = [self.metadata[i] for i in keep] + metadata
        self._save()

    def remove_document(self, document_id: str) -> bool:
        if not any(item["document_id"] == document_id for item in self.metadata): return False
        keep = [i for i, item in enumerate(self.metadata) if item["document_id"] != document_id]
        self.vectors = self.vectors[keep] if keep else np.empty((0, 0), dtype="float32")
        self.metadata = [self.metadata[i] for i in keep]; self._save(); return True

    def search(self, vector: list[float], top_k: int) -> list[tuple[dict, float]]:
        if not self.metadata: return []
        matrix = self._normalize(self.vectors.copy()); query = self._normalize(np.asarray([vector], dtype="float32"))
        index = faiss.IndexFlatIP(matrix.shape[1]); index.add(matrix)
        scores, ids = index.search(query, min(top_k, len(self.metadata)))
        return [(self.metadata[i], float(score)) for score, i in zip(scores[0], ids[0]) if i >= 0]

    def documents(self) -> list[dict]:
        seen = {}
        for item in self.metadata: seen[item["document_id"]] = {k: item[k] for k in ("document_id", "filename")}
        return list(seen.values())

    def _save(self) -> None:
        np.save(self.vectors_file, self.vectors)
        self.metadata_file.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        if self.vectors.size:
            index = faiss.IndexFlatIP(self.vectors.shape[1]); index.add(self._normalize(self.vectors.copy()))
            faiss.write_index(index, str(self.index_file))
        elif self.index_file.exists():
            self.index_file.unlink()
    @staticmethod
    def _normalize(values):
        norms = np.linalg.norm(values, axis=1, keepdims=True); norms[norms == 0] = 1
        return values / norms


vector_store = VectorStoreService()
