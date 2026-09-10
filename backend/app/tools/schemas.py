"""Typed input and output contracts for controlled Phase 5 tools.

These Pydantic models are the validation boundary between an agent tool
request and the limited local functions the backend permits to execute.
"""

from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeSearchInput(BaseModel):
    """Validated arguments for semantic search of indexed local documents."""

    query: str = Field(
        min_length=1,
        max_length=2_000,
        description="Local knowledge-base query.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum source chunks to retrieve.",
    )


class DocumentIdInput(BaseModel):
    """Validated reference to an existing locally controlled document."""

    document_id: str = Field(description="Server-issued local document identifier.")


class CalculatorInput(BaseModel):
    """Deterministic arithmetic request; expressions are never executed as Python."""

    operation: Literal["add", "subtract", "multiply", "divide", "percentage", "average"] = Field(
        description="Approved deterministic arithmetic operation."
    )
    values: list[float] = Field(
        min_length=1,
        max_length=50,
        description="Numeric operands; expressions and code are not accepted.",
    )


class ToolResult(BaseModel):
    """Normalized observation returned after one controlled tool invocation.

    This is an operational result, not a model rationale. Source references
    preserve document traceability for knowledge-search observations.
    """

    tool: str = Field(description="Registered tool ID that was requested.")
    success: bool = Field(description="Whether controlled execution completed successfully.")
    data: dict[str, object] | None = Field(
        default=None,
        description="Structured successful output, when available.",
    )
    error: str | None = Field(
        default=None,
        description="Sanitized failure message, when execution was unsuccessful.",
    )
    sources: list[dict[str, str]] = Field(
        default_factory=list,
        description="Source identifiers propagated by local knowledge retrieval.",
    )
