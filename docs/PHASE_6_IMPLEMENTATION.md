# Phase 6: Local OCR, Vision, Reliability, and Progress

OCR uses the `OCRService` abstraction with local Tesseract through
`pytesseract`; Windows users must install the Tesseract executable separately.
PyMuPDF renders scanned PDF pages locally. Searchable PDFs keep the existing
fast parser path; text-poor PDFs attempt OCR and retain Phase 2 `ocr_required`
behavior if optional OCR dependencies are unavailable. PNG, JPG, and JPEG are
validated, stored by server-issued IDs, OCR processed, and can use existing RAG.

Vision uses the configurable `VISION_MODEL` (default `llava:7b`) through the
existing local Ollama service and registered `vision` model role. Routes are
`POST /api/vision/{document_id}/analyze` and `/ask`; no URL or filesystem path
is accepted. OCR and vision output are untrusted data. Weak image OCR invokes
strict local transcription; OCR/vision technical-token conflicts are retained,
never guessed. Isolated conflicts become `user_confirmation_required`; broad
uncertainty becomes `reupload_required`. A confirmation at
`POST /api/documents/{id}/confirm-extraction` stores OCR evidence, vision
evidence, the chosen/manual value, and `verification_source=user` separately.

Final reliability states are `accepted`, `accepted_with_warnings`,
`user_confirmation_required`, `review_required`, and `reupload_required`.
Only the first two may enter RAG. OCR-needed documents are therefore indexable
when their final reliability is acceptable.

Long document processing creates a local, server-generated job ID on document
metadata. `GET /api/jobs/{job_id}` exposes safe stage-first status only. Job
state is in-memory, protected by a lock, and intentionally replaceable with
persistent storage later; it contains no document content or filesystem paths.
`waiting_for_user` supports the confirmation flow without holding an HTTP
request open. CPU-only operation is
supported where local Tesseract/Ollama models can run, but may be slow.
