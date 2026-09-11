"""Knowledge indexing and grounded retrieval orchestration for local RAG."""

from typing import TypedDict

from app.core.config import settings
from app.services.knowledge.chunking_service import chunking_service
from app.services.documents.document_service import document_service
from app.services.knowledge.embedding_service import embedding_service
from app.services.knowledge.vector_store_service import ChunkMetadata, vector_store


class IndexingResult(TypedDict):
    """Summary returned after successfully indexing a source document."""

    document_id: str
    status: str
    chunk_count: int
    embedding_model: str


class RetrievedChunk(ChunkMetadata):
    """A source-traceable chunk augmented with its retrieval similarity score."""

    similarity_score: float


class KnowledgeService:
    """Coordinate local document chunking, embedding, indexing, and retrieval."""

    def index(self, document_id: str) -> IndexingResult:
        """Chunk and embed a stored document, then replace its knowledge index.

        Args:
            document_id: ID of a document already accepted by document storage.

        Returns:
            Indexing status, chunk count, and the embedding model used.

        Raises:
            ValueError: If extraction produced no indexable text.
        """
        document_metadata = document_service.get_metadata(document_id)
        # SECURITY: documents explicitly marked as unreadable must not pollute
        # the local vector store with untrusted gibberish or missing values.
        if document_metadata.reliability_status not in {"accepted", "accepted_with_warnings"}:
            raise ValueError("Document extraction quality is insufficient for reliable indexing.")
        document_text = document_service.get_text(document_id)
        chunks = chunking_service.chunk(document_id, document_text)
        if not chunks:
            raise ValueError("Document has no extractable text to index.")
        vectors = embedding_service.embed([chunk.text for chunk in chunks])
        # Metadata travels with every vector, allowing returned evidence to be
        # traced to its document, filename, chunk position, and exact text.
        records: list[ChunkMetadata] = [
            {
                "document_id": document_id,
                "filename": document_metadata.filename,
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "character_count": chunk.character_count,
            }
            for chunk in chunks
        ]
        # Re-indexing replaces prior chunks for this document, preventing stale
        # content from being retrieved after an explicit indexing operation.
        vector_store.replace_document(document_id, vectors, records)
        return {
            "document_id": document_id,
            "status": "indexed",
            "chunk_count": len(chunks),
            "embedding_model": settings.embedding_model,
        }

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """Retrieve source evidence most similar to a user query.

        The response contains only locally indexed chunks plus their scores;
        callers use this traceable evidence to ground a later model response.
        """
        vector = embedding_service.embed([query])[0]
        return [
            {**record, "similarity_score": score}
            for record, score in vector_store.search(vector, top_k)
        ]

    def remove(self, document_id: str) -> bool:
        """Remove a document's indexed evidence while leaving source files intact."""
        return vector_store.remove_document(document_id)


knowledge_service = KnowledgeService()
