from app.core.config import settings
from app.services.chunking_service import chunking_service
from app.services.document_service import DocumentNotFoundError, document_service
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store


class KnowledgeService:
    def index(self, document_id: str) -> dict:
        meta = document_service.get_metadata(document_id); text = document_service.get_text(document_id)
        chunks = chunking_service.chunk(document_id, text)
        if not chunks: raise ValueError("Document has no extractable text to index.")
        vectors = embedding_service.embed([chunk.text for chunk in chunks])
        records = [{"document_id": document_id, "filename": meta.filename, "chunk_id": c.chunk_id, "chunk_index": c.chunk_index, "text": c.text, "character_count": c.character_count} for c in chunks]
        vector_store.replace_document(document_id, vectors, records)
        return {"document_id": document_id, "status": "indexed", "chunk_count": len(chunks), "embedding_model": settings.embedding_model}
    def search(self, query: str, top_k: int):
        vector = embedding_service.embed([query])[0]
        return [{**record, "similarity_score": score} for record, score in vector_store.search(vector, top_k)]
    def remove(self, document_id: str) -> bool: return vector_store.remove_document(document_id)


knowledge_service = KnowledgeService()
