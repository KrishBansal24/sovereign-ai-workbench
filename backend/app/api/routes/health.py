import logging

from fastapi import APIRouter

from app.core.config import settings
from app.services.ollama_service import ollama_service


router = APIRouter(prefix="/api", tags=["system"])
logger = logging.getLogger(__name__)


@router.get(
    "/health",
    summary="Report local backend and Ollama status",
    description="Returns backend health without sending any information outside the local machine.",
)
def health() -> dict[str, str]:
    ollama_available = ollama_service.is_available()
    model_status = (
        "available" if ollama_available and ollama_service.is_model_available() else "unavailable"
    )
    logger.info(
        "event=health_check endpoint=/api/health ollama=%s model=%s model_status=%s",
        "available" if ollama_available else "unavailable",
        settings.ollama_model,
        model_status,
    )
    return {
        "backend": "online",
        "ollama": "available" if ollama_available else "unavailable",
        "model": settings.ollama_model,
        "model_status": model_status,
        "mode": "local",
    }
