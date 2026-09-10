"""Document HTTP routes delegating storage and extraction to ``DocumentService``."""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentTextResponse,
)
from app.services.document_service import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentServiceError,
    DocumentStorageError,
    DocumentValidationError,
    document_service,
)


router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post(
    "/upload",
    response_model=DocumentMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract one local document",
    description="Stores a PDF, TXT, or DOCX file locally and extracts text without using an LLM.",
)
async def upload_document(file: Annotated[UploadFile, File(description="A PDF, TXT, or DOCX file")]) -> DocumentMetadata:
    """Accept one supported document and delegate validation and extraction.

    Args:
        file: Multipart PDF, TXT, or DOCX upload supplied by the client.

    Returns:
        Sanitized document metadata created by ``DocumentService``.
    """
    started_at = time.perf_counter()
    try:
        # SECURITY: service-side validation controls file type, size, storage
        # name, and parser selection; the route never derives a filesystem path.
        content = await file.read()
        metadata = document_service.upload(file.filename, content, file.content_type)
    except DocumentValidationError as error:
        _log_failure(started_at, "validation_error")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except DocumentProcessingError as error:
        _log_failure(started_at, "extraction_error")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except (DocumentStorageError, DocumentServiceError) as error:
        _log_failure(started_at, "storage_error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be processed locally.",
        ) from error
    finally:
        await file.close()

    duration_ms = (time.perf_counter() - started_at) * 1_000
    logger.info(
        "event=document_upload_completed endpoint=/api/documents/upload document_id=%s file_type=%s size_bytes=%s duration_ms=%.2f character_count=%s success=true",
        metadata.document_id,
        metadata.file_type,
        metadata.size_bytes,
        duration_ms,
        metadata.character_count,
    )
    return metadata


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List locally stored documents",
    description="Returns metadata only, newest upload first.",
)
def list_documents() -> DocumentListResponse:
    """List local document metadata by delegating to ``DocumentService``."""
    return DocumentListResponse(documents=document_service.list_documents())


@router.get(
    "/{document_id}",
    response_model=DocumentMetadata,
    summary="Get document processing metadata",
)
def get_document(document_id: str) -> DocumentMetadata:
    """Return metadata for one validated document ID.

    Args:
        document_id: Server-issued document UUID.
    """
    return _get_metadata(document_id)


@router.get(
    "/{document_id}/text",
    response_model=DocumentTextResponse,
    summary="Get extracted document text",
    description="Development endpoint. Future access control can protect extracted content.",
)
def get_document_text(document_id: str) -> DocumentTextResponse:
    """Return previously extracted text for a controlled document ID.

    Args:
        document_id: Server-issued document UUID.

    Returns:
        Document ID and extracted local text.
    """
    try:
        text = document_service.get_text(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from error
    except DocumentStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The extracted text could not be read.",
        ) from error
    return DocumentTextResponse(document_id=document_id, text=text)


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a stored document and its extracted text",
)
def delete_document(document_id: str) -> DeleteDocumentResponse:
    """Delete a stored document and ask the service to remove its RAG vectors.

    Args:
        document_id: Server-issued document UUID.

    Returns:
        Confirmation that controlled document artifacts were removed.
    """
    try:
        document_service.delete(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from error
    except DocumentStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document could not be deleted.",
        ) from error
    logger.info("event=document_deleted endpoint=/api/documents document_id=%s success=true", document_id)
    return DeleteDocumentResponse(document_id=document_id, deleted=True)


def _get_metadata(document_id: str) -> DocumentMetadata:
    """Delegate metadata lookup and map service errors to HTTP responses."""
    try:
        return document_service.get_metadata(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from error
    except DocumentStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The document metadata could not be read.",
        ) from error


def _log_failure(started_at: float, error_type: str) -> None:
    """Log an upload failure category without retaining untrusted file content."""
    duration_ms = (time.perf_counter() - started_at) * 1_000
    logger.warning(
        "event=document_upload_failed endpoint=/api/documents/upload duration_ms=%.2f success=false error_type=%s",
        duration_ms,
        error_type,
    )
