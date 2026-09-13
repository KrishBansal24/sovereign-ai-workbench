"""Controlled listing and download endpoints for generated local artifacts."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.artifacts import ArtifactMetadata
from app.services.artifact_service import ArtifactNotFoundError, artifact_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactMetadata])
def list_artifacts() -> list[ArtifactMetadata]:
    """List safe metadata for locally generated artifacts."""
    return artifact_service.list()


@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: str) -> FileResponse:
    """Download only a file addressed by a server-issued artifact identifier."""
    try:
        path = artifact_service.path(artifact_id)
    except ArtifactNotFoundError as error:
        raise HTTPException(status_code=404, detail="Artifact not found.") from error
    return FileResponse(path, filename=path.name.split("_", 1)[-1])
