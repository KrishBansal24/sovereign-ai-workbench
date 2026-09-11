"""Registered local-model status routes backed by ``ModelManager``."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.models import ModelInfo
from app.services.llm.model_manager import RegisteredModel, UnknownModelError, model_manager
from app.services.llm.ollama_service import OllamaUnavailableError


router = APIRouter(prefix="/api/models", tags=["models"])


def as_model_info(model: RegisteredModel) -> ModelInfo:
    """Map an internal registry entry to a safe API status response.

    Args:
        model: Application-approved local model definition.

    Returns:
        Public metadata with current local availability.
    """
    try:
        available = model_manager.is_available(model)
    except OllamaUnavailableError:
        available = False
    return ModelInfo(
        id=model.id,
        display_name=model.display_name,
        ollama_model=model.ollama_model,
        capabilities=list(model.capabilities),
        enabled=model.enabled,
        available=available,
        description=model.description,
    )


@router.get("", response_model=list[ModelInfo], summary="List registered local models and availability")
def list_models() -> list[ModelInfo]:
    """List approved model roles and their current local availability."""
    return [as_model_info(model) for model in model_manager.list()]


@router.get("/{model_id}", response_model=ModelInfo, summary="Get one registered local model")
def get_model(model_id: str) -> ModelInfo:
    """Get one approved model role by its stable application identifier.

    Args:
        model_id: Registered role ID, such as ``general`` or ``coding``.

    Returns:
        Public status for the selected local model role.
    """
    try:
        return as_model_info(model_manager.get(model_id))
    except UnknownModelError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registered model not found.") from error
