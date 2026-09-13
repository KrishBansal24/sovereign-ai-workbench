"""Typed API contracts for locally stored and extracted documents."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


from app.schemas.enums import DocumentReliabilityStatus, ExtractionStatus, FileType


class ExtractionDisagreement(BaseModel):
    """Unresolved technical field evidence retained for user confirmation."""

    field_or_token: str = Field(description="Visible technical token or field label.")
    ocr_value: str = Field(description="Raw OCR candidate; never silently replaced.")
    vision_value: str = Field(description="Raw vision candidate; never silently replaced.")
    severity: Literal["high"] = Field(default="high")


class ExtractionConfirmation(BaseModel):
    """Validated user choice for one server-recorded disagreement."""

    field_or_token: str = Field(min_length=1)
    selected_source: Literal["ocr", "vision", "manual"]
    manual_value: str | None = Field(default=None, max_length=200)


class DocumentMetadata(BaseModel):
    """Safe metadata about a Phase 2 document; internal paths are excluded."""

    document_id: str = Field(description="Generated identifier used for controlled document access.")
    filename: str = Field(description="Original filename retained as metadata only.")
    file_type: FileType = Field(description="Validated supported document type.")
    size_bytes: int = Field(description="Original upload size in bytes.")
    uploaded_at: datetime = Field(description="UTC timestamp at local upload processing.")
    status: Literal["processed"] = Field(description="Current successful processing state.")
    text_extracted: bool = Field(description="Whether non-empty extractable text was found.")
    character_count: int = Field(description="Number of extracted text characters.")
    extraction_status: ExtractionStatus = Field(description="Extraction outcome; OCR is deferred when required.")
    page_count: int | None = Field(default=None, description="PDF page count when available; never fabricated for other files.")
    extraction_method: str = Field(default="parser", description="Backend-derived extraction provenance.")
    reliability_status: DocumentReliabilityStatus = Field(default=DocumentReliabilityStatus.ACCEPTED, description="Final extraction reliability decision used by indexing policy.")
    extraction_warnings: list[str] = Field(default_factory=list, description="Safe user-facing extraction warnings.")
    extraction_disagreements: list[ExtractionDisagreement] = Field(default_factory=list, description="Unresolved OCR/vision evidence requiring confirmation.")
    confirmations: list[dict[str, str]] = Field(default_factory=list, description="User confirmation provenance without changing raw OCR or vision evidence.")
    job_id: str | None = Field(default=None, description="Optional server-generated processing-progress identifier.")
    processed_pages: int | None = Field(default=None, description="Pages examined during page-aware processing.")
    text_pages: list[int] = Field(default_factory=list, description="Pages with usable embedded text.")
    ocr_pages: list[int] = Field(default_factory=list, description="Pages processed through local OCR.")
    unprocessed_ocr_pages: list[int] = Field(default_factory=list, description="Scan pages outside configured OCR safety bounds.")
    index_eligible: bool = Field(default=False, description="Backend-authoritative eligibility for local knowledge indexing.")
    structured_metadata: dict[str, object] = Field(default_factory=dict, description="Safe derived source structure such as lines, headings, or CSV columns.")


class DocumentListResponse(BaseModel):
    """Metadata-only listing of documents currently held in controlled storage."""
    documents: list[DocumentMetadata]
    total: int = Field(default=0, description="Total documents matching the listing request.")
    limit: int = Field(default=50, description="Maximum records returned in this page.")
    offset: int = Field(default=0, description="Zero-based page offset.")
    has_more: bool = Field(default=False, description="Whether a subsequent page exists.")


class DocumentTextResponse(BaseModel):
    """Extracted text returned by the development document-text endpoint."""
    document_id: str
    text: str


class DeleteDocumentResponse(BaseModel):
    """Confirmation that controlled document artifacts were removed."""
    document_id: str
    deleted: Literal[True]
