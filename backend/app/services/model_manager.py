"""Registry and availability manager for configuration-driven local models.

Routes and routers use this service instead of hardcoding Ollama model names.
It queries the existing local Ollama service and applies configured fallback.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.services.ollama_service import OllamaUnavailableError, ollama_service


@dataclass(frozen=True)
class RegisteredModel:
    """Immutable definition of one application-approved local model role."""
    id: str
    display_name: str
    ollama_model: str
    capabilities: tuple[str, ...]
    enabled: bool
    priority: int
    fallback_model_id: str | None
    description: str


class UnknownModelError(Exception):
    """Raised when an ID is not present in the controlled registry."""


class DisabledModelError(Exception):
    """Raised when an otherwise known model is disabled by policy."""


class NoModelAvailableError(Exception):
    """Raised when neither the preferred model nor its fallback is local."""


class ModelManager:
    """Resolve registered roles, capabilities, availability, and safe fallback."""

    def __init__(self, registry: tuple[RegisteredModel, ...] | None = None) -> None:
        """Build the approved local-model registry or accept a test registry.

        Args:
            registry: Optional immutable model definitions. When omitted, roles
                are populated from the locally configured Ollama model names.
        """
        self.registry = registry or (
            RegisteredModel(
                id="general", display_name="Qwen3 8B", ollama_model=settings.general_model,
                capabilities=("general", "reasoning", "analysis", "summarization", "document_analysis"),
                enabled=True, priority=1, fallback_model_id=None,
                description="General local reasoning and document-analysis model.",
            ),
            RegisteredModel(
                id="coding", display_name="Qwen2.5 Coder 7B", ollama_model=settings.coding_model,
                capabilities=("coding", "debugging", "code_explanation", "refactoring"),
                enabled=True, priority=1, fallback_model_id="general",
                description="Local coding, debugging, and code-explanation model.",
            ),
        )

    def get(self, model_id: str) -> RegisteredModel:
        """Return one registered model or raise UnknownModelError."""
        for model in self.registry:
            if model.id == model_id:
                return model
        raise UnknownModelError("Registered model not found.")

    def list(self) -> tuple[RegisteredModel, ...]:
        """Return the immutable registry in configured priority order."""
        return self.registry

    def by_capability(self, capability: str) -> tuple[RegisteredModel, ...]:
        """Return enabled models declaring the requested capability."""
        return tuple(model for model in self.registry if capability in model.capabilities and model.enabled)

    def available_ids(self) -> set[str]:
        """Return enabled registry IDs whose exact names appear in local Ollama."""
        names = ollama_service.get_available_model_names()
        return {model.id for model in self.registry if model.enabled and model.ollama_model in names}

    def is_available(self, model: RegisteredModel) -> bool:
        """Check one registered model without exposing raw Ollama data."""
        return model.id in self.available_ids()

    def select(self, preferred_id: str) -> tuple[RegisteredModel, bool, str | None]:
        """Choose an available registered model, optionally using configured fallback."""
        # SECURITY: callers can select only registry IDs, never arbitrary models.
        preferred = self.get(preferred_id)
        if not preferred.enabled:
            raise DisabledModelError("The requested model is disabled.")
        available = self.available_ids()
        if preferred.id in available:
            return preferred, False, None
        if preferred.fallback_model_id:
            fallback = self.get(preferred.fallback_model_id)
            if fallback.enabled and fallback.id in available:
                return fallback, True, f"Configured {preferred.id} model was unavailable."
        raise NoModelAvailableError("No suitable registered local model is available.")


model_manager = ModelManager()
