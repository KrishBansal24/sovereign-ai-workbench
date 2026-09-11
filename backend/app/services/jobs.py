"""Thread-safe in-memory job state for local operations.

This intentionally stores only safe status metadata. It is process-local and
therefore replaceable with persistent storage when deployment needs demand it.
"""

from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from app.schemas.jobs import JobStatus, ProcessingJob


class JobNotFoundError(Exception):
    """Raised when a client supplies an unknown server-issued job identifier."""


class JobProgressService:
    """Manage bounded, server-generated progress records without background workers."""

    def __init__(self) -> None:
        """Create the protected in-memory job registry."""
        self._jobs: dict[str, ProcessingJob] = {}
        self._lock = RLock()

    def create(self, operation: str, stage: str, message: str) -> ProcessingJob:
        """Create a queued job for a backend-defined operation."""
        now = datetime.now(UTC)
        job = ProcessingJob(job_id=str(uuid4()), operation=operation, status="queued", stage=stage, message=message, created_at=now, updated_at=now)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def update(self, job_id: str, status: JobStatus, stage: str, message: str, progress: int | None = None, result: dict[str, str] | None = None) -> ProcessingJob:
        """Atomically update safe state; callers never store document content here."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFoundError("Job not found.")
            updated = job.model_copy(update={"status": status, "stage": stage, "message": message, "progress": progress, "result": result or job.result, "updated_at": datetime.now(UTC)})
            self._jobs[job_id] = updated
            return updated

    def get(self, job_id: str) -> ProcessingJob:
        """Return one safe job record by its server-generated identifier."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFoundError("Job not found.")
            return job


job_progress_service = JobProgressService()
