from datetime import datetime
from typing import Literal

from pydantic import BaseModel


FileType = Literal["pdf", "txt", "docx"]
ExtractionStatus = Literal["extracted", "ocr_required"]


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: FileType
    size_bytes: int
    uploaded_at: datetime
    status: Literal["processed"]
    text_extracted: bool
    character_count: int
    extraction_status: ExtractionStatus
    page_count: int | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]


class DocumentTextResponse(BaseModel):
    document_id: str
    text: str


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: Literal[True]
