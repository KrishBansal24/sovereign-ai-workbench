# Phase 2 Implementation — Document Ingestion & Processing

Status: complete and verified.

## Objective

Phase 2 adds a secure local document foundation for later retrieval, OCR, vision, and agent workflows. It accepts PDF, TXT, and DOCX files; stores them locally; extracts deterministic text; and exposes metadata APIs. No LLM is used for basic extraction.

## Architecture

```text
FastAPI document route → DocumentService → PDF/TXT/DOCX parser → controlled local storage
```

`DocumentService` uses a lightweight JSON metadata file under `backend/data/documents`. This is sufficient for a single-machine Phase 2 development foundation and keeps persistence replaceable by a future database. Original files are retained under UUID-derived names, extracted text is stored separately, and metadata stores no internal file path.

## Validation and storage

- Allowed extensions: `.pdf`, `.txt`, `.docx`
- MIME type is checked when supplied; PDF header and DOCX ZIP-package signatures are also checked.
- Empty files and files larger than `MAX_UPLOAD_SIZE_MB` (default 20 MB) are rejected.
- The original filename is metadata only. A UUID plus trusted extension is the stored filename, preventing traversal, collisions, and arbitrary overwrite/delete.
- Deletion uses only a validated, recorded UUID and removes the document, extracted text, and metadata.

## Extraction

- **PDF:** `pypdf` extracts page text and reports page count. Corrupt/encrypted PDFs fail safely. Text-poor or image-only PDFs are marked `ocr_required`; OCR is deliberately not implemented.
- **TXT:** tries UTF-8 with BOM, UTF-16, and CP1252 before a replacement fallback; line endings and nulls are conservatively normalized.
- **DOCX:** `python-docx` extracts paragraphs and table rows locally.

## Endpoints

| Method | Endpoint | Result |
| --- | --- | --- |
| POST | `/api/documents/upload` | Stores and processes one upload |
| GET | `/api/documents` | Metadata list, newest first |
| GET | `/api/documents/{document_id}` | One metadata record |
| GET | `/api/documents/{document_id}/text` | Extracted text for development/testing |
| DELETE | `/api/documents/{document_id}` | Safely deletes local artifacts |

## Privacy and limitations

Application logs record document ID, type, size, duration, success/failure, and character count only. They do not record uploaded file bytes or extracted text. This phase has no authentication, malware scanning, OCR, image understanding, RAG, embeddings, or document analysis via LLM. The text endpoint is intended for development and must receive access controls in a future security phase.

## Tests

`tests/test_documents_api.py` uses temporary storage and synthetic in-memory TXT, blank PDF, and DOCX files. It covers upload, extraction, unsupported/empty/oversized files, filename safety, retrieval, listing, deletion, missing IDs, and corrupt PDFs. No proprietary MRPL documents or actual Ollama model are used.
