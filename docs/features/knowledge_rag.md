# Knowledge / RAG

The Knowledge system provides Retrieval-Augmented Generation (RAG) using exclusively local embeddings and inference, guaranteeing data confidentiality.

## Indexing

When a document is marked as `index_eligible` (see [OCR / Vision](ocr_vision.md)), it can be added to the Knowledge base:
1. **Chunking:** The document text is chunked into overlapping segments to preserve context.
2. **Embeddings Generation:** The local backend calls Ollama using the configured embedding model (e.g., `nomic-embed-text`) to generate dense vectors.
3. **FAISS Storage:** Vectors are stored in a local, persistent FAISS index (`IndexFlatIP`) utilizing L2-normalized vectors and cosine similarity.

## Retrieval and Generation

When a user or the Agent queries the knowledge base:
1. **Vector Search:** The query is embedded, and FAISS returns the top-K chunks.
2. **Context Assembly:** Chunks are formatted alongside strict system instructions into a prompt.
3. **Grounded Generation:** The reasoning model (e.g., `qwen3:8b`) generates an answer based *only* on the provided chunks.

## Hallucination Resistance

The backend enforces strict anti-hallucination policies:
- **Insufficient Evidence:** If the retrieved chunks do not contain the answer, the model is instructed to refuse to answer rather than hallucinate external knowledge.
- **Source Citation:** The model must cite the source chunks used. The backend propagates the exact `document_id` of the sources back to the user interface.
- **Eligibility:** Documents with garbled text or failed OCR are blocked from entering the index, ensuring the model is not confused by corrupted context.
