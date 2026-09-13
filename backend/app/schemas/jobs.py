"""Safe public contracts for local long-running operation progress."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "waiting_for_user", "completed", "failed"]


class ProcessingJob(BaseModel):
    """Server-created progress record without paths, content, or secrets."""

    job_id: str = Field(description="Server-generated opaque progress identifier.")
    operation: str = Field(description="Backend-defined operation category.")
    status: JobStatus = Field(description="Current lifecycle state.")
    stage: str = Field(description="Human-readable backend processing stage.")
    progress: int | None = Field(default=None, ge=0, le=100, description="Approximate progress when determinable.")
    message: str = Field(description="Safe user-facing progress message.")
    created_at: datetime
    updated_at: datetime
    result: dict[str, str] | None = Field(default=None, description="Safe completion identifiers only; never document content or paths.")
    display_name: str | None = Field(default=None, description="Friendly task label for product interfaces; never an ID or path.")
    resource_name: str | None = Field(default=None, description="Safe related filename or generated-file label.")
    resource_type: str | None = Field(default=None, description="Safe related resource category such as document or artifact.")
