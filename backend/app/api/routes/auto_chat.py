"""Automatic local-model routing endpoint for classified user tasks."""

import logging
import time

from fastapi import APIRouter, HTTPException, status

from app.schemas.models import AutoChatRequest, AutoChatResponse
from app.services.llm.model_manager import DisabledModelError, NoModelAvailableError, UnknownModelError
from app.services.llm.model_router import model_router
from app.services.llm.ollama_service import OllamaResponseError, OllamaUnavailableError, ollama_service
from app.services.llm.task_classifier import task_classifier


router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/auto",
    response_model=AutoChatResponse,
    summary="Automatically route a task to a registered local model",
    description="Classifies the task and delegates only to approved local Ollama models.",
)
def auto_chat(request: AutoChatRequest) -> AutoChatResponse:
    """Classify, route, and execute a request through local model services.

    Args:
        request: Validated message and optional registered model-role override.

    Returns:
        Local model output together with explainable routing metadata.
    """
    started_at = time.perf_counter()
    # SECURITY: ModelRouter accepts controlled registry IDs, never arbitrary
    # model tags supplied by a client.
    classification = task_classifier.classify(request.message)
    try:
        model, routing = model_router.route(classification, request.model)
        response = ollama_service.chat_with_model(model.ollama_model, request.message)
    except UnknownModelError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown registered model override.") from error
    except DisabledModelError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested model is disabled.") from error
    except NoModelAvailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No suitable local model is available.") from error
    except OllamaUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Local Ollama is unavailable.") from error
    except OllamaResponseError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Local Ollama could not complete the request.") from error
    logger.info(
        "event=auto_chat_completed task_type=%s selected_model_id=%s "
        "selected_ollama_model=%s fallback_used=%s duration_ms=%.2f success=true",
        routing.task_type,
        routing.selected_model_id,
        routing.selected_model,
        routing.fallback_used,
        (time.perf_counter() - started_at) * 1_000,
    )
    return AutoChatResponse(response=response, routing=routing, processing="local")
