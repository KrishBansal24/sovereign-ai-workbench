# API Reference — Phase 1

Base URL: `http://127.0.0.1:8000`.

## `GET /api/health`

Purpose: diagnose backend, local Ollama, and configured-model availability. It returns HTTP 200 even if Ollama is unavailable because the FastAPI backend is still reachable.

Example response:

```json
{"backend":"online","ollama":"available","model":"qwen3:8b","model_status":"available","mode":"local"}
```

`ollama` can be `unavailable`; `model_status` is then `unavailable` because it cannot be verified.

## `POST /api/chat`

Purpose: submit a message to the configured local Ollama model.

Request:

```json
{"message":"Explain what a P&ID is."}
```

Successful response:

```json
{"response":"...","model":"qwen3:8b","processing":"local"}
```

An empty or missing message returns 422. Unavailable Ollama returns 503. A missing configured model returns 404. An invalid/unexpected local runtime response returns 502. Swagger at `/docs` supplies the live OpenAPI schema.

## `POST /api/documents/upload`

Purpose: upload one PDF, TXT, or DOCX document, store it locally under a generated identifier, and extract text without an LLM. Send multipart form-data with a `file` field. Maximum size is controlled by `MAX_UPLOAD_SIZE_MB` (20 MB by default).

Example response:

```json
{"document_id":"uuid","filename":"inspection_report.pdf","file_type":"pdf","size_bytes":1234,"status":"processed","text_extracted":true,"character_count":900,"extraction_status":"extracted","page_count":3}
```

Invalid type, MIME mismatch, empty file, excessive size, corrupt file, or unreadable encrypted PDF returns 422. Text-poor PDFs are stored successfully with `extraction_status: "ocr_required"`; no OCR is attempted.

## Document retrieval

- `GET /api/documents` lists metadata newest first.
- `GET /api/documents/{document_id}` returns one metadata record.
- `GET /api/documents/{document_id}/text` returns extracted text for development/testing.
- `DELETE /api/documents/{document_id}` deletes the stored file, extracted text, and metadata.

An unknown or malformed document ID returns 404. Internal filesystem paths are never returned.
