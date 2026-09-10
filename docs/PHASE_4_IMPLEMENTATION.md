# Phase 4 — Local Knowledge Base / RAG

Phase 4 is complete and verified. It uses `nomic-embed-text` through local Ollama and a persisted FAISS cosine-similarity index under ignored runtime storage in `backend/data/knowledge`.

Documents are explicitly indexed through `POST /api/knowledge/documents/{document_id}/index`; uploads are not indexed automatically. Text is chunked with configurable overlap, embedded locally, and stored with document ID, filename, chunk ID, and text. Re-indexing replaces prior chunks for that document.

`POST /api/knowledge/search` returns retrieved chunks and `similarity_score` (cosine similarity, not confidence). `POST /api/knowledge/ask` retrieves context, routes the grounded request through the existing general/document-analysis model path, and derives sources from backend retrieval metadata. If no chunks exist, it returns an insufficient-information response.

No cloud embeddings, hosted vector database, RAG framework, OCR, agent loop, or automatic document indexing is used. The current RAG prompt instructs the model to use only retrieved local context, but model output is not a formal citation verifier; the returned source list is backend-derived.
