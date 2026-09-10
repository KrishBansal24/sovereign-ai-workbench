"""Request and response contracts for local chat and model-routed chat APIs."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """User message accepted by the Phase 1 local chat endpoint."""

    message: str = Field(min_length=1, max_length=20_000, description="Non-empty prompt processed only locally.")


class ChatResponse(BaseModel):
    """Local model response returned by the basic chat endpoint."""

    response: str = Field(description="Generated local-model text.")
    model: str = Field(description="Configured Ollama model used for inference.")
    processing: Literal["local"] = Field(description="Confirms local-only processing.")
