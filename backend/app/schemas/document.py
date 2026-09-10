"""Typed API contracts for locally stored and extracted documents."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FileType = Literal["pdf", "txt", "docx"]
ExtractionStatus = Literal["extracted", "ocr_required"]


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


class DocumentListResponse(BaseModel):
    """Metadata-only listing of documents currently held in controlled storage."""
    documents: list[DocumentMetadata]


class DocumentTextResponse(BaseModel):
    """Extracted text returned by the development document-text endpoint."""
    document_id: str
    text: str


class DeleteDocumentResponse(BaseModel):
    """Confirmation that controlled document artifacts were removed."""
    document_id: str
    deleted: Literal[True]
