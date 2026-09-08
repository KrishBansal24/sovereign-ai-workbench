from typing import Literal

from pydantic import BaseModel, Field


TaskType = Literal[
    "general", "reasoning", "coding", "debugging", "code_explanation", "document_analysis", "summarization"
]


class ModelInfo(BaseModel):
    id: str
    display_name: str
    ollama_model: str
    capabilities: list[str]
    enabled: bool
    available: bool
    description: str


class RoutingMetadata(BaseModel):
    task_type: TaskType
    selected_model_id: str
    selected_model: str
    selection_reason: str
    fallback_used: bool
    fallback_reason: str | None = None


class AutoChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    model: str | None = Field(default=None, description="Optional registered model ID: general or coding.")


class AutoChatResponse(BaseModel):
    response: str
    routing: RoutingMetadata
    processing: Literal["local"]
