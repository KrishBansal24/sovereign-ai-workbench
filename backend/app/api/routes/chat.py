import logging
import time

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ollama_service import (
    OllamaModelNotFoundError,
    OllamaResponseError,
    OllamaUnavailableError,
    ollama_service,
)


router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the configured local model",
    description="Processes the message only through the local Ollama server.",
    response_description="The local model response and selected configured model.",
)
def chat(request: ChatRequest) -> ChatResponse:
    started_at = time.perf_counter()
    logger.info("event=chat_request_received endpoint=/api/chat model=%s", settings.ollama_model)
    try:
        response = ollama_service.chat(request.message)
    except OllamaUnavailableError as error:
        _log_failure(started_at, "ollama_unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local Ollama is unavailable. Start Ollama and try again.",
        ) from error
    except OllamaModelNotFoundError as error:
        _log_failure(started_at, "model_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configured local model '{settings.ollama_model}' was not found.",
        ) from error
    except OllamaResponseError as error:
        _log_failure(started_at, "ollama_response_error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Local Ollama could not complete the request.",
        ) from error

    duration_ms = (time.perf_counter() - started_at) * 1_000
    logger.info(
        "event=chat_request_completed endpoint=/api/chat model=%s duration_ms=%.2f success=true",
        settings.ollama_model,
        duration_ms,
    )
    return ChatResponse(
        response=response,
        model=settings.ollama_model,
        processing="local",
    )


def _log_failure(started_at: float, error_type: str) -> None:
    duration_ms = (time.perf_counter() - started_at) * 1_000
    logger.warning(
        "event=chat_request_failed endpoint=/api/chat model=%s duration_ms=%.2f success=false error_type=%s",
        settings.ollama_model,
        duration_ms,
        error_type,
    )
