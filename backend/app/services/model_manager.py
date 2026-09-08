"""Configuration-driven model registry and local availability management."""

from dataclasses import dataclass

from app.core.config import settings
from app.services.ollama_service import OllamaUnavailableError, ollama_service


@dataclass(frozen=True)
class RegisteredModel:
    id: str
    display_name: str
    ollama_model: str
    capabilities: tuple[str, ...]
    enabled: bool
    priority: int
    fallback_model_id: str | None
    description: str


class UnknownModelError(Exception):
    pass


class DisabledModelError(Exception):
    pass


class NoModelAvailableError(Exception):
    pass


class ModelManager:
    def __init__(self, registry: tuple[RegisteredModel, ...] | None = None) -> None:
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
        for model in self.registry:
            if model.id == model_id:
                return model
        raise UnknownModelError("Registered model not found.")

    def list(self) -> tuple[RegisteredModel, ...]:
        return self.registry

    def by_capability(self, capability: str) -> tuple[RegisteredModel, ...]:
        return tuple(model for model in self.registry if capability in model.capabilities and model.enabled)

    def available_ids(self) -> set[str]:
        names = ollama_service.get_available_model_names()
        return {model.id for model in self.registry if model.enabled and model.ollama_model in names}

    def is_available(self, model: RegisteredModel) -> bool:
        return model.id in self.available_ids()

    def select(self, preferred_id: str) -> tuple[RegisteredModel, bool, str | None]:
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
