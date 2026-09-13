"""Centralized enumerations for API contracts and internal states."""

from enum import Enum


class DocumentReliabilityStatus(str, Enum):
    """Final extraction reliability decision used by indexing policy."""
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
    REVIEW_REQUIRED = "review_required"
    REUPLOAD_REQUIRED = "reupload_required"


class FileType(str, Enum):
    """Validated supported document types."""
    PDF = "pdf"
    TXT = "txt"
    PY = "py"
    MD = "md"
    CSV = "csv"
    XLSX = "xlsx"
    DOCX = "docx"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"


class ExtractionStatus(str, Enum):
    """Extraction outcomes."""
    EXTRACTED = "extracted"
    OCR_REQUIRED = "ocr_required"
    OCR_EXTRACTED = "ocr_extracted"


class QualityStatus(str, Enum):
    """Image/OCR quality statuses."""
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNINGS = "accepted_with_warnings"
    REVIEW_REQUIRED = "review_required"
    REUPLOAD_REQUIRED = "reupload_required"
