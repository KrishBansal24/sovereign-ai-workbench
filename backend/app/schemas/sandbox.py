"""Public contracts for bounded local Python sandbox execution."""

from typing import Literal

from pydantic import BaseModel, Field


class SandboxExecutionRequest(BaseModel):
    """Untrusted Python source submitted to the controlled local sandbox."""

    code: str = Field(min_length=1, max_length=20_000, description="Python source executed only in a server-created workspace.")


class SandboxGenerationRequest(BaseModel):
    """A bounded local coding-model task; raw models and paths are excluded."""
    task: str = Field(min_length=1, max_length=4_000)


class SandboxArtifact(BaseModel):
    """Safe metadata for a file produced inside a sandbox workspace."""

    artifact_id: str
    filename: str
    size_bytes: int
    validation_status: Literal["validated", "invalid"] = "validated"


class SandboxExecutionResult(BaseModel):
    """Structured result that never reveals host paths or environment secrets."""

    execution_id: str
    status: Literal["success", "failed", "timeout", "rejected"]
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: float
    artifacts: list[SandboxArtifact] = Field(default_factory=list)
    job_id: str | None = None
