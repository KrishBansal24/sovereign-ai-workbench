"""Unit tests for local RAG chunk overlap and persistent vector retrieval."""

from pathlib import Path
from types import SimpleNamespace

from app.services.knowledge.chunking_service import ChunkingService
from app.services.knowledge.vector_store_service import VectorStoreService


def test_chunking_and_overlap(monkeypatch):
    from app.services.knowledge import chunking_service as module
    monkeypatch.setattr(
        module,
        "settings",
        SimpleNamespace(rag_chunk_size=20, rag_chunk_overlap=5),
    )
    chunks = ChunkingService().chunk("doc", "A" * 45)
    assert len(chunks) == 3
    assert chunks[0].chunk_id == "doc:0"


def test_vector_store_persists_searches_and_removes(tmp_path: Path) -> None:
    store = VectorStoreService(tmp_path)
    store.replace_document(
        "d1",
        [[1, 0], [0, 1]],
        [
            {"document_id": "d1", "filename": "pump.txt", "chunk_id": "d1:0"},
            {"document_id": "d1", "filename": "pump.txt", "chunk_id": "d1:1"},
        ],
    )
    assert store.search([1, 0], 1)[0][0]["chunk_id"] == "d1:0"
    assert (tmp_path / "index.faiss").exists()
    assert VectorStoreService(tmp_path).documents()[0]["document_id"] == "d1"
    assert store.remove_document("d1")
    assert store.search([1, 0], 5) == []
