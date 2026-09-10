"""Map classified work to controlled local model roles and explanations."""

from app.schemas.models import RoutingMetadata
from app.services.model_manager import ModelManager, RegisteredModel, model_manager
from app.services.task_classifier import Classification


TASK_MODEL_IDS = {
    "coding": "coding", "debugging": "coding", "code_explanation": "coding",
    "general": "general", "reasoning": "general", "document_analysis": "general", "summarization": "general",
}


class ModelRouter:
    """Bridge TaskClassifier output to ModelManager selection and fallback."""

    def __init__(self, manager: ModelManager = model_manager) -> None:
        """Create a router backed by the approved local model manager.

        Args:
            manager: Registry and availability service, replaceable in tests.
        """
        self.manager = manager

    def route(self, classification: Classification, override_model_id: str | None = None) -> tuple[RegisteredModel, RoutingMetadata]:
        """Route a task or registered override to an available local model.

        Args:
            classification: Deterministic task-family result to route.
            override_model_id: Optional approved registry ID requested by a
                caller; raw Ollama model names are never accepted.

        Returns:
            The selected registered model and safe, user-visible routing data.
        """
        # SECURITY: overrides remain registry IDs; router never accepts Ollama names.
        requested_id = override_model_id or TASK_MODEL_IDS[classification.task_type]
        selected, fallback_used, fallback_reason = self.manager.select(requested_id)
        if override_model_id:
            reason = f"Selected registered model override '{override_model_id}'."
        elif fallback_used:
            reason = "General model used because the preferred local model was unavailable."
        elif requested_id == "coding":
            reason = "Selected coding model because the task requires programming assistance."
        else:
            reason = "Selected general model because the task requires conceptual analysis or general assistance."
        return selected, RoutingMetadata(
            task_type=classification.task_type, selected_model_id=selected.id,
            selected_model=selected.ollama_model, selection_reason=reason,
            fallback_used=fallback_used, fallback_reason=fallback_reason,
        )


model_router = ModelRouter()
