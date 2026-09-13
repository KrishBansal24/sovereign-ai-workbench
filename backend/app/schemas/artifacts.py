"""Safe metadata contracts for locally generated Phase 7 artifacts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ArtifactMetadata(BaseModel):
    """Public artifact record that deliberately excludes its host path."""

    artifact_id: str
    filename: str
    media_type: str
    artifact_type: Literal["sandbox", "analysis", "document", "spreadsheet", "presentation", "pdf", "chart"]
    size_bytes: int
    created_at: datetime
    validation_status: Literal["validated", "invalid"]
    source_tool: str
    job_id: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
