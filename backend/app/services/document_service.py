"""Controlled local document storage, metadata, and deterministic extraction.

DocumentService is the boundary between untrusted uploads and parser/storage
implementations. It uses UUID-derived internal names rather than raw filenames.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.document import DocumentMetadata
from app.services.parsers import docx_parser, pdf_parser, text_parser


class DocumentServiceError(Exception):
    """Base exception for document processing failures."""


class DocumentValidationError(DocumentServiceError):
    """The upload does not satisfy the supported-file requirements."""


class DocumentNotFoundError(DocumentServiceError):
    """The requested document does not exist."""


class DocumentProcessingError(DocumentServiceError):
    """A supported file could not be extracted safely."""


class DocumentStorageError(DocumentServiceError):
    """The local document store could not complete an operation."""


ALLOWED_TYPES = {".pdf": "pdf", ".txt": "txt", ".docx": "docx"}
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf", "application/x-pdf"},
    "txt": {"text/plain"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}
OCR_TEXT_THRESHOLD = 20


class DocumentService:
    """Coordinate upload validation, controlled storage, parsers, and metadata.

    JSON metadata is intentionally lightweight for Phase 2 and can later be
    replaced without exposing storage paths through API routes.
    """

    def __init__(
        self,
        data_directory: Path | None = None,
        max_upload_size_mb: int | None = None,
    ) -> None:
        """Initialize controlled storage using configured defaults when omitted.

        Args:
            data_directory: Optional root for document artifacts and metadata.
            max_upload_size_mb: Optional test or deployment upload-size limit.
        """
        self.data_directory = data_directory or settings.data_directory
        self.max_upload_bytes = (max_upload_size_mb or settings.max_upload_size_mb) * 1024 * 1024
        self.documents_directory = self.data_directory / "documents"
        self.files_directory = self.documents_directory / "files"
        self.texts_directory = self.documents_directory / "texts"
        self.metadata_file = self.documents_directory / "metadata.json"
        self._ensure_storage()

    def upload(self, filename: str | None, content: bytes, content_type: str | None) -> DocumentMetadata:
        """Validate, store, extract, and record one local document upload."""
        file_type, extension = self._validate_upload(filename, content, content_type)
        # SECURITY: raw filenames never choose storage paths or overwrite files.
        document_id = str(uuid.uuid4())
        stored_name = f"{document_id}{extension}"
        stored_file = self.files_directory / stored_name

        try:
            stored_file.write_bytes(content)
            extracted_text, page_count = self._extract(file_type, content)
            # Text-poor PDFs are retained but honestly marked for future OCR.
            extraction_status = "extracted" if len(extracted_text.strip()) >= OCR_TEXT_THRESHOLD else "ocr_required"
            text_file = self.texts_directory / f"{document_id}.txt"
            text_file.write_text(extracted_text, encoding="utf-8")
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=Path(filename or "").name,
                file_type=file_type,
                size_bytes=len(content),
                uploaded_at=datetime.now(UTC),
                status="processed",
                text_extracted=bool(extracted_text.strip()),
                character_count=len(extracted_text),
                extraction_status=extraction_status,
                page_count=page_count,
            )
            records = self._load_records()
            records[document_id] = metadata.model_dump(mode="json")
            self._save_records(records)
            return metadata
        except (OSError, docx_parser.DocxExtractionError, pdf_parser.PdfExtractionError) as error:
            self._remove_artifacts(document_id, stored_name)
            if isinstance(error, OSError):
                raise DocumentStorageError("The document could not be stored locally.") from error
            raise DocumentProcessingError(str(error)) from error

    def get_metadata(self, document_id: str) -> DocumentMetadata:
        """Return controlled metadata for one validated document identifier."""
        return self._get_record(document_id)

    def list_documents(self) -> list[DocumentMetadata]:
        """List local metadata newest first without exposing file paths."""
        records = self._load_records()
        documents = [DocumentMetadata.model_validate(item) for item in records.values()]
        return sorted(documents, key=lambda item: item.uploaded_at, reverse=True)

    def get_text(self, document_id: str) -> str:
        """Read extracted text only after document-ID validation."""
        self._get_record(document_id)
        text_file = self.texts_directory / f"{document_id}.txt"
        try:
            return text_file.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise DocumentNotFoundError("Extracted text is not available for this document.") from error
        except OSError as error:
            raise DocumentStorageError("The extracted text could not be read.") from error

    def delete(self, document_id: str) -> None:
        """Delete controlled file/text/metadata artifacts and linked RAG vectors."""
        metadata = self._get_record(document_id)
        extension = f".{metadata.file_type}"
        try:
            (self.files_directory / f"{document_id}{extension}").unlink(missing_ok=True)
            (self.texts_directory / f"{document_id}.txt").unlink(missing_ok=True)
            records = self._load_records()
            records.pop(document_id, None)
            self._save_records(records)
            # Keep Phase 4's explicit knowledge base free of orphaned vectors.
            try:
                from app.services.vector_store_service import vector_store
                vector_store.remove_document(document_id)
            except Exception:
                pass
        except OSError as error:
            raise DocumentStorageError("The document could not be deleted.") from error

    def _validate_upload(self, filename: str | None, content: bytes, content_type: str | None) -> tuple[str, str]:
        """Validate filename-derived type, size, MIME, and lightweight signatures."""
        if not filename:
            raise DocumentValidationError("A filename is required.")
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_TYPES:
            raise DocumentValidationError("Only PDF, TXT, and DOCX files are supported.")
        if not content:
            raise DocumentValidationError("Empty files are not supported.")
        if len(content) > self.max_upload_bytes:
            raise DocumentValidationError("The file exceeds the configured upload-size limit.")
        file_type = ALLOWED_TYPES[extension]
        if content_type and content_type != "application/octet-stream":
            if content_type.lower() not in ALLOWED_MIME_TYPES[file_type]:
                raise DocumentValidationError("The supplied MIME type does not match the file extension.")
        if file_type == "pdf" and not content.startswith(b"%PDF-"):
            raise DocumentValidationError("The uploaded file is not a valid PDF.")
        if file_type == "docx" and not content.startswith(b"PK"):
            raise DocumentValidationError("The uploaded file is not a valid DOCX package.")
        return file_type, extension

    def _extract(self, file_type: str, content: bytes) -> tuple[str, int | None]:
        """Dispatch validated content to exactly one deterministic parser."""
        if file_type == "pdf":
            return pdf_parser.extract_text(content)
        if file_type == "docx":
            return docx_parser.extract_text(content), None
        return text_parser.extract_text(content), None

    def _ensure_storage(self) -> None:
        """Create controlled runtime directories and an empty metadata store."""
        try:
            self.files_directory.mkdir(parents=True, exist_ok=True)
            self.texts_directory.mkdir(parents=True, exist_ok=True)
            if not self.metadata_file.exists():
                self._save_records({})
        except OSError as error:
            raise DocumentStorageError("The local document store could not be initialized.") from error

    def _load_records(self) -> dict[str, dict[str, object]]:
        """Load serialized metadata or raise a controlled storage error."""
        try:
            return json.loads(self.metadata_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DocumentStorageError("The document metadata store is unavailable.") from error

    def _save_records(self, records: dict[str, dict[str, object]]) -> None:
        """Atomically replace metadata after writing a temporary JSON file."""
        temporary_file = self.metadata_file.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
        os.replace(temporary_file, self.metadata_file)

    def _get_record(self, document_id: str) -> DocumentMetadata:
        """Validate a UUID-shaped ID and return its recorded metadata."""
        try:
            uuid.UUID(document_id)
        except ValueError as error:
            raise DocumentNotFoundError("Document not found.") from error
        records = self._load_records()
        record = records.get(document_id)
        if not record:
            raise DocumentNotFoundError("Document not found.")
        return DocumentMetadata.model_validate(record)

    def _remove_artifacts(self, document_id: str, stored_name: str) -> None:
        """Remove partial artifacts after failed storage or extraction."""
        (self.files_directory / stored_name).unlink(missing_ok=True)
        (self.texts_directory / f"{document_id}.txt").unlink(missing_ok=True)


document_service = DocumentService()
