"""Read-only progress endpoints for project-wide local processing jobs."""

from fastapi import APIRouter, HTTPException, Response

from app.schemas.jobs import ProcessingJob
from app.services.jobs import JobNotFoundError, job_progress_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ProcessingJob, summary="Get safe local operation progress")
def get_job(job_id: str, response: Response) -> ProcessingJob:
    """Return stage-first progress for a server-generated job identifier."""
    try:
        response.headers["Cache-Control"] = "no-store"
        return job_progress_service.get(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found.") from error
