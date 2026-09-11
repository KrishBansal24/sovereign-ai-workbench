"""Local-only image vision routes for server-issued document identifiers."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.documents.document_service import DocumentNotFoundError
from app.services.llm.ollama_service import OllamaServiceError
from app.services.llm.model_manager import NoModelAvailableError
from app.services.multimodal.vision_service import VisionResult, vision_service


router = APIRouter(prefix="/api/vision", tags=["vision"])


class VisionQuestion(BaseModel):
    """Optional local question about one uploaded image."""

    question: str = Field(min_length=1, max_length=4_000)


def _analyze(document_id: str, question: str | None) -> VisionResult:
    """Delegate controlled image lookup and local model errors to the service."""
    try:
        return vision_service.analyze(document_id, question)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail="Document not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (OllamaServiceError, NoModelAvailableError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Local vision model is unavailable.") from error


@router.post("/{document_id}/analyze", response_model=VisionResult, summary="Analyze an uploaded image locally")
def analyze_image(document_id: str) -> VisionResult:
    """Describe technical content in one controlled PNG or JPEG image."""
    return _analyze(document_id, None)


@router.post("/{document_id}/ask", response_model=VisionResult, summary="Ask a local model about an uploaded image")
def ask_image(document_id: str, request: VisionQuestion) -> VisionResult:
    """Answer a question about one controlled uploaded image."""
    return _analyze(document_id, request.question)
