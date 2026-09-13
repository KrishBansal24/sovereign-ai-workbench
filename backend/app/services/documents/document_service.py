"""Controlled local document storage, metadata, and deterministic extraction.

DocumentService is the boundary between untrusted uploads and parser/storage
implementations. It uses UUID-derived internal names rather than raw filenames.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

from app.core.config import settings
from app.schemas.document import DocumentMetadata, ExtractionConfirmation
from app.schemas.enums import DocumentReliabilityStatus
from app.services.jobs import job_progress_service
from app.services.documents.parsers import csv_parser, docx_parser, pdf_parser, source_parser, text_parser
from app.services.multimodal.ocr_service import OCRProcessingError, OCRUnavailableError, ocr_service
from app.services.multimodal.extraction_reliability_service import extraction_reliability_service
from app.services.multimodal.ocr_quality_service import ocr_quality_service
from openpyxl import load_workbook


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


ALLOWED_TYPES = {".pdf": "pdf", ".txt": "txt", ".py": "py", ".md": "md", ".csv": "csv", ".xlsx": "xlsx", ".docx": "docx", ".png": "png", ".jpg": "jpg", ".jpeg": "jpeg"}
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf", "application/x-pdf"},
    "txt": {"text/plain"},
    "py": {"text/x-python", "application/x-python-code", "text/plain"},
    "md": {"text/markdown", "text/plain"},
    # httpx and common Windows applications identify CSV as this legacy Excel
    # MIME type. It remains a CSV only when the filename and parser agree.
    "csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
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
        # Background upload jobs may finish concurrently. Protect each metadata
        # read-modify-write so one completed upload cannot replace another's
        # record (or race over the temporary metadata file).
        self._records_lock = RLock()
        self._ensure_storage()

    def upload(self, filename: str | None, content: bytes, content_type: str | None, job_id: str | None = None) -> DocumentMetadata:
        """Validate, store, extract, and record one local document upload."""
        job = job_progress_service.get(job_id) if job_id else job_progress_service.create("document_processing", "uploaded", "Document uploaded for local processing.")
        job_progress_service.update(job.job_id, "running", "quality_check", "Checking document extraction requirements.", 10)
        file_type, extension = self._validate_upload(filename, content, content_type)
        # SECURITY: raw filenames never choose storage paths or overwrite files.
        document_id = str(uuid.uuid4())
        stored_name = f"{document_id}{extension}"
        stored_file = self.files_directory / stored_name

        try:
            stored_file.write_bytes(content)
            job_progress_service.update(job.job_id, "running", "ocr_processing", "Extracting text locally.", 40)
            extracted_text, page_count, origin, reliability_status, extraction_warnings, page_details = self._extract(file_type, content)
            if len(extracted_text) > settings.document_max_extracted_chars:
                extracted_text = extracted_text[:settings.document_max_extracted_chars]
                extraction_warnings.append("Extracted text reached the configured document character safety limit.")
                reliability_status = "review_required"
            # Text-poor PDFs are retained but honestly marked for future OCR.
            has_meaningful_text = len(extracted_text.strip()) >= OCR_TEXT_THRESHOLD
            # Running OCR is not itself success: blank/scanned pages remain
            # honestly marked for OCR review when no usable text was detected.
            extraction_status = (
                "ocr_extracted"
                if origin == "ocr" and has_meaningful_text
                else ("extracted" if has_meaningful_text else "ocr_required")
            )
            text_file = self.texts_directory / f"{document_id}.txt"
            job_progress_service.update(job.job_id, "running", "verifying_extraction", "Evaluating extraction reliability.", 85)
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
                extraction_method=origin,
                reliability_status=reliability_status,
                extraction_warnings=extraction_warnings,
                extraction_disagreements=[item.model_dump() for item in getattr(reliability, "important_disagreements", [])] if 'reliability' in locals() and reliability else [],
                job_id=job.job_id,
                processed_pages=page_details.get("processed_pages"),
                text_pages=page_details.get("text_pages", []),
                ocr_pages=page_details.get("ocr_pages", []),
                unprocessed_ocr_pages=page_details.get("unprocessed_ocr_pages", []),
                index_eligible=reliability_status in {"accepted", "accepted_with_warnings"},
                structured_metadata=page_details.get("structured_metadata", {}),
            )
            with self._records_lock:
                records = self._load_records()
                records[document_id] = metadata.model_dump(mode="json")
                self._save_records(records)
            final_status = "waiting_for_user" if metadata.reliability_status == "user_confirmation_required" else "completed"
            final_stage = "user_confirmation" if final_status == "waiting_for_user" else "completed"
            job_progress_service.update(job.job_id, final_status, final_stage, "One technical value requires confirmation." if final_status == "waiting_for_user" else "Document processing completed.", 100, {"document_id": document_id})
            return metadata
        except (OSError, docx_parser.DocxExtractionError, pdf_parser.PdfExtractionError, OCRProcessingError, OCRUnavailableError) as error:
            job_progress_service.update(job.job_id, "failed", "failed", "Document processing could not be completed.")
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
        extension = f".{metadata.file_type.value}"
        try:
            (self.files_directory / f"{document_id}{extension}").unlink(missing_ok=True)
            (self.texts_directory / f"{document_id}.txt").unlink(missing_ok=True)
            with self._records_lock:
                records = self._load_records()
                records.pop(document_id, None)
                self._save_records(records)
            # Keep Phase 4's explicit knowledge base free of orphaned vectors.
            try:
                from app.services.knowledge.vector_store_service import vector_store
                vector_store.remove_document(document_id)
            except Exception:
                pass
        except OSError as error:
            raise DocumentStorageError("The document could not be deleted.") from error

    def confirm_extraction(self, document_id: str, confirmation: ExtractionConfirmation) -> DocumentMetadata:
        """Store a validated user decision while retaining raw OCR/vision evidence."""
        metadata = self._get_record(document_id)
        match = next((item for item in metadata.extraction_disagreements if item.field_or_token == confirmation.field_or_token), None)
        if match is None:
            raise DocumentValidationError("The requested confirmation field is not pending.")
        if confirmation.selected_source == "manual" and not (confirmation.manual_value or "").strip():
            raise DocumentValidationError("A manual value is required when selected_source is manual.")
        confirmed_value = confirmation.manual_value.strip() if confirmation.selected_source == "manual" else (match.ocr_value if confirmation.selected_source == "ocr" else match.vision_value)
        provenance = {"field_or_token": match.field_or_token, "ocr_value": match.ocr_value, "vision_value": match.vision_value, "user_confirmed_value": confirmed_value, "verification_source": "user"}
        remaining = [item for item in metadata.extraction_disagreements if item.field_or_token != match.field_or_token]
        updated = metadata.model_copy(update={"extraction_disagreements": remaining, "confirmations": [*metadata.confirmations, provenance], "reliability_status": DocumentReliabilityStatus.ACCEPTED_WITH_WARNINGS if not remaining else DocumentReliabilityStatus.USER_CONFIRMATION_REQUIRED, "index_eligible": not remaining})
        with self._records_lock:
            records = self._load_records()
            records[document_id] = updated.model_dump(mode="json")
            self._save_records(records)
        if updated.job_id and not remaining:
            job_progress_service.update(updated.job_id, "completed", "completed", "Extraction confirmation completed.", 100)
        return updated

    def _validate_upload(self, filename: str | None, content: bytes, content_type: str | None) -> tuple[str, str]:
        """Validate filename-derived type, size, MIME, and lightweight signatures."""
        if not filename:
            raise DocumentValidationError("A filename is required.")
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_TYPES:
            raise DocumentValidationError("Only PDF, TXT, Python, Markdown, CSV, XLSX, DOCX, PNG, JPG, and JPEG files are supported.")
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
        if file_type in {"docx", "xlsx"} and not content.startswith(b"PK"):
            raise DocumentValidationError("The uploaded file is not a valid Office package.")
        if file_type == "png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise DocumentValidationError("The uploaded file is not a valid PNG.")
        if file_type in {"jpg", "jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise DocumentValidationError("The uploaded file is not a valid JPEG.")
        return file_type, extension

    def _extract(self, file_type: str, content: bytes) -> tuple[str, int | None, str, str, list[str], dict[str, object]]:
        """Dispatch validated content to exactly one deterministic parser."""
        if file_type == "pdf":
            pages = pdf_parser.extract_pages(content)
            text_pages = [page.page_number for page in pages if page.usable]
            ocr_needed = [page.page_number for page in pages if not page.usable]
            merged = {page.page_number: page.text for page in pages if page.usable}
            warnings: list[str] = []
            ocr_pages: list[int] = []
            unprocessed = ocr_needed[settings.ocr_max_pages:]
            to_ocr = ocr_needed[:settings.ocr_max_pages]
            try:
                if to_ocr:
                    result = ocr_service.pdf(content, to_ocr)
                    merged.update({page.page_number: page.text for page in result.pages})
                    ocr_pages = to_ocr
                text = "\n\n".join(f"[Page {number}]\n{merged.get(number, '')}" for number in range(1, len(pages) + 1) if merged.get(number, "").strip())
                if unprocessed:
                    warnings.append(f"{len(unprocessed)} scan page(s) were not OCR processed because of the configured OCR page limit.")
                if not ocr_needed:
                    return text, len(pages), "parser", "accepted", warnings, {"processed_pages": len(pages), "text_pages": text_pages, "ocr_pages": [], "unprocessed_ocr_pages": []}
                reliability = extraction_reliability_service.decide(result.quality or ocr_quality_service.assess_text(result.text))
                status = "review_required" if unprocessed else reliability.status
                return text, len(pages), "mixed_parser_ocr", status, warnings + reliability.issues + reliability.warnings, {"processed_pages": len(pages) - len(unprocessed), "text_pages": text_pages, "ocr_pages": ocr_pages, "unprocessed_ocr_pages": unprocessed}
            except (OCRUnavailableError, OCRProcessingError):
                # Preserve Phase 2's usable upload path until Windows Tesseract
                # and the optional local renderer are installed.
                text = "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in pages if page.usable)
                return text, len(pages), "parser", "review_required", ["OCR is unavailable for one or more scanned PDF pages."], {"processed_pages": len(text_pages), "text_pages": text_pages, "ocr_pages": [], "unprocessed_ocr_pages": ocr_needed}
        if file_type == "docx":
            return docx_parser.extract_text(content), None, "parser", "accepted", [], {}
        if file_type == "xlsx":
            from io import BytesIO
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))[:100]
            return "\n".join(", ".join("" if value is None else str(value) for value in row) for row in rows), None, "parser", "accepted", [], {}
        if file_type == "py":
            text, metadata = source_parser.extract_python(content)
            return text, None, "python_source", "accepted", [], {"structured_metadata": metadata}
        if file_type == "md":
            text, metadata = source_parser.extract_markdown(content)
            return text, None, "markdown", "accepted", [], {"structured_metadata": metadata}
        if file_type == "csv":
            try:
                text, metadata = csv_parser.extract_csv(content)
            except ValueError as error:
                raise DocumentProcessingError(str(error)) from error
            return text, None, "csv", "accepted", [], {"structured_metadata": metadata}
        if file_type in {"png", "jpg", "jpeg"}:
            result = ocr_service.image(content)
            reliability = extraction_reliability_service.decide(result.quality) if result.quality else None
            if reliability and not reliability.can_index:
                try:
                    from app.services.multimodal.vision_service import vision_service
                    transcription = vision_service.transcribe_bytes(content)
                    reliability = extraction_reliability_service.decide_with_vision(result.text, result.quality, transcription.text)
                    return result.text, 1, "ocr_vision_agreement" if reliability.can_index else "ocr_vision_disagreement", reliability.status, reliability.issues + reliability.warnings, {}
                except Exception:
                    pass
            return result.text, 1, result.extraction_method, reliability.status if reliability else "review_required", (reliability.issues + reliability.warnings) if reliability else ["OCR quality could not be assessed."], {}
        return text_parser.extract_text(content), None, "parser", "accepted", [], {}

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
        # A unique name prevents a second background upload from removing this
        # writer's staging file before ``os.replace``. Callers that modify the
        # mapping also hold ``_records_lock`` to preserve both updates.
        temporary_file = self.metadata_file.with_name(f"{self.metadata_file.name}.{uuid.uuid4().hex}.tmp")
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
