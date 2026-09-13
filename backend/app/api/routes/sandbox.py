"""Temporary local API for controlled Phase 7 Python execution."""

from fastapi import APIRouter

from app.schemas.sandbox import SandboxExecutionRequest, SandboxExecutionResult, SandboxGenerationRequest
from app.services.sandbox_service import sandbox_service

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


@router.post("/execute", response_model=SandboxExecutionResult, summary="Execute bounded Python in a local workspace")
def execute(request: SandboxExecutionRequest) -> SandboxExecutionResult:
    """Execute untrusted code only through the isolated subprocess service."""
    return sandbox_service.execute(request.code)


@router.post("/generate", response_model=SandboxExecutionResult, summary="Generate and bounded-repair local Python using the registered coding model")
def generate(request: SandboxGenerationRequest) -> SandboxExecutionResult:
    """Run at most the configured number of local coding-model repair attempts."""
    return sandbox_service.generate_and_execute(request.task)
