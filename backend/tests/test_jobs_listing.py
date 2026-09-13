"""Recent-job listing stays safe and user-facing clients need no job UUID input."""
from app.services.jobs import JobProgressService


def test_recent_jobs_are_returned_newest_first() -> None:
    service = JobProgressService()
    first = service.create("document_processing", "queued", "Queued")
    second = service.create("data_analysis", "queued", "Queued")
    service.update(first.job_id, "running", "reading_data", "Working")
    jobs = service.list()
    assert [job.job_id for job in jobs] == [first.job_id, second.job_id]
    assert jobs[0].operation == "document_processing"


def test_job_can_expose_safe_friendly_display_metadata() -> None:
    service = JobProgressService()
    job = service.create(
        "document_processing", "queued", "Queued",
        display_name="Upload — inspection scan.pdf",
        resource_name="inspection scan.pdf",
        resource_type="document",
    )
    assert job.display_name == "Upload — inspection scan.pdf"
    assert job.resource_name == "inspection scan.pdf"
    assert job.resource_type == "document"
