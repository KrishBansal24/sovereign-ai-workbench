"""Schemas for registered local-model status and explainable routing decisions."""

from typing import Literal

from pydantic import BaseModel, Field


TaskType = Literal[
    "general", "reasoning", "coding", "debugging", "code_explanation", "document_analysis", "summarization"
]


class ModelInfo(BaseModel):
    """Public status of one application-registered local model role."""
    id: str
    display_name: str
    ollama_model: str
    capabilities: list[str]
    enabled: bool
    available: bool
    description: str


class RoutingMetadata(BaseModel):
    """Operational routing explanation that excludes hidden model reasoning."""
    task_type: TaskType
    selected_model_id: str
    selected_model: str
    selection_reason: str
    fallback_used: bool
    fallback_reason: str | None = None


class AutoChatRequest(BaseModel):
    """Request for automatic local-model routing with an optional safe override."""
    message: str = Field(min_length=1, max_length=20_000, description="Task supplied for local classification and inference.")
    model: str | None = Field(default=None, description="Optional registered model ID: general or coding.")


class AutoChatResponse(BaseModel):
    """Model response paired with backend-generated routing metadata."""
    response: str
    routing: RoutingMetadata
    processing: Literal["local"]
