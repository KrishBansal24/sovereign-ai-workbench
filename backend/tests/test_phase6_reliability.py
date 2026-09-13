"""Deterministic tests for Phase 6 reliability, confirmation, and job state."""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.document import DocumentMetadata, ExtractionConfirmation, ExtractionDisagreement
from app.schemas.jobs import ProcessingJob
from app.schemas.enums import DocumentReliabilityStatus
from app.services.documents.document_service import DocumentService
from app.services.jobs import JobProgressService
from app.services.multimodal.extraction_reliability_service import extraction_reliability_service
from app.services.multimodal.ocr_quality_service import OCRQualityResult


def _review_quality() -> OCRQualityResult:
    """Return deterministic weak-but-readable OCR quality."""
    return OCRQualityResult(status="review_required", score=0.5, reasons=["weak"], extracted_character_count=30, suspicious_character_ratio=0.0, requires_retry=True, requires_review=True)


def test_isolated_ocr_vision_disagreement_requires_confirmation() -> None:
    """One technical mismatch is preserved for a human rather than guessed."""
    result = extraction_reliability_service.decide_with_vision("P-202 72 C", _review_quality(), "P-202 12 C")
    assert result.status == "user_confirmation_required"
    assert result.important_disagreements[0].ocr_value == "72 C"


def test_confirmation_preserves_raw_evidence_and_unblocks_document(tmp_path) -> None:
    """A valid OCR selection keeps both candidates and records user provenance."""
    service = DocumentService(data_directory=tmp_path)
    document_id = str(uuid4())
    metadata = DocumentMetadata(document_id=document_id, filename="report.png", file_type="png", size_bytes=1, uploaded_at=datetime.now(UTC), status="processed", text_extracted=True, character_count=10, extraction_status="ocr_extracted", reliability_status=DocumentReliabilityStatus.USER_CONFIRMATION_REQUIRED, extraction_disagreements=[ExtractionDisagreement(field_or_token="technical_measurement", ocr_value="72 C", vision_value="12 C")])
    service._save_records({document_id: metadata.model_dump(mode="json")})
    updated = service.confirm_extraction(document_id, ExtractionConfirmation(field_or_token="technical_measurement", selected_source="ocr"))
    assert updated.reliability_status == DocumentReliabilityStatus.ACCEPTED_WITH_WARNINGS
    assert updated.confirmations[0]["user_confirmed_value"] == "72 C"
    assert updated.confirmations[0]["vision_value"] == "12 C"


def test_job_service_exposes_safe_waiting_state() -> None:
    """Generic jobs support stage-first progress and waiting-for-user state."""
    jobs = JobProgressService()
    job = jobs.create("document_processing", "uploaded", "Uploaded.")
    waiting = jobs.update(job.job_id, "waiting_for_user", "user_confirmation", "One value requires confirmation.", 90)
    assert waiting.status == "waiting_for_user"
    assert "path" not in waiting.model_dump()
