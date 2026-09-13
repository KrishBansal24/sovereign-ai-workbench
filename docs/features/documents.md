# Documents

The Sovereign AI Workbench securely handles the ingestion, extraction, and lifecycle of multiple document formats.

## Ingestion and Supported Formats

The workbench natively supports text extraction from standard formats. Uploaded documents are parsed deterministically when possible:
- **Text & Code:** `.txt`, `.md`, `.csv`, `.py` (Ingested strictly as inert text)
- **Documents:** `.pdf`, `.docx`
- **Images/Scans:** `.png`, `.jpg`, `.jpeg` (Processed via OCR/Vision)

## Metadata and Server-Generated IDs

Upon upload, the backend assigns a secure `document_id` (UUID). The filesystem and RAG database never rely on the user-provided filename for internal linking. Metadata includes original filename, content type, processing status, and indexing eligibility.

## Document Lifecycle

1. **Upload:** File is streamed to the backend and stored securely in local app data directories.
2. **Parsing / Extraction:** The appropriate parser extracts raw text.
3. **Assessment:** The OCR/Vision service grades the extraction (see [OCR / Vision](ocr_vision.md)).
4. **Knowledge State:** Documents proven reliable (or manually approved) are marked `index_eligible: true`.
5. **Management:** Documents can be listed, viewed, or deleted by the user via the TUI.

## Security Handling of Python Source

When a `.py` file is uploaded as a document, it is intentionally treated as untrusted, inert text. The document ingestion service will not execute uploaded code. This allows safe RAG context over internal proprietary codebases.
