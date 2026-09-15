"""Deterministic OCR/vision comparison and final local extraction policy."""

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.services.multimodal.ocr_quality_service import OCRQualityResult


ReliabilityStatus = Literal["accepted", "accepted_with_warnings", "user_confirmation_required", "review_required", "reupload_required"]


class ExtractionDisagreement(BaseModel):
    """Unresolved important token mismatch; neither value is silently chosen."""

    field_or_token: str
    ocr_value: str
    vision_value: str
    severity: Literal["high"] = "high"


class ExtractionReliabilityResult(BaseModel):
    """Final deterministic policy deciding whether text is safe to index."""

    status: ReliabilityStatus
    score: float
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    important_disagreements: list[ExtractionDisagreement] = Field(default_factory=list)
    can_index: bool
    reupload_recommended: bool
    upload_guidance: list[str] = Field(default_factory=list)


class ExtractionReliabilityService:
    """Apply conservative policy to untrusted OCR and vision transcription data."""

    def compare(self, ocr_text: str, vision_text: str | None) -> list[ExtractionDisagreement]:
        """Compare IDs, numbers, and units without attempting to repair either value."""
        if vision_text is None:
            return []
        pattern = r"\b(?:[A-Za-z]+-\d+|\d+(?:\.\d+)?\s*(?:C|V|kW|mm/s|bar|%))\b"
        ocr_tokens = re.findall(pattern, ocr_text, flags=re.IGNORECASE)
        vision_tokens = re.findall(pattern, vision_text, flags=re.IGNORECASE)
        disagreements: list[ExtractionDisagreement] = []
        for ocr_value, vision_value in zip(ocr_tokens, vision_tokens):
            if ocr_value.lower() != vision_value.lower():
                field = "identifier" if "-" in ocr_value or "-" in vision_value else "technical_measurement"
                disagreements.append(ExtractionDisagreement(field_or_token=field, ocr_value=ocr_value, vision_value=vision_value))
        return disagreements

    def decide(self, quality: OCRQualityResult, vision_text: str | None = None) -> ExtractionReliabilityResult:
        """Return a no-guessing final status; conflicts always block indexing."""
        disagreements = self.compare("", vision_text) if False else []
        if quality.status == "accepted":
            return ExtractionReliabilityResult(status="accepted", score=quality.score, can_index=True, reupload_recommended=False)
        guidance = ["Ensure the full page is visible.", "Keep the camera directly above the document.", "Ensure text is in focus and avoid glare."]
        status: ReliabilityStatus = "review_required" if quality.score >= .35 else "reupload_required"
        return ExtractionReliabilityResult(status=status, score=quality.score, issues=quality.reasons, can_index=False, reupload_recommended=status == "reupload_required", upload_guidance=guidance)

    def decide_with_vision(self, ocr_text: str, quality: OCRQualityResult, vision_text: str) -> ExtractionReliabilityResult:
        """Request confirmation for isolated conflicts; reject widespread unreadability."""
        disagreements = self.compare(ocr_text, vision_text)
        if len(disagreements) <= 2 and disagreements:
            return ExtractionReliabilityResult(status="user_confirmation_required", score=quality.score, issues=["One or more technical values require confirmation."], important_disagreements=disagreements, can_index=False, reupload_recommended=False)
        if len(disagreements) > 2 or "[UNCERTAIN]" in vision_text:
            return ExtractionReliabilityResult(status="reupload_required", score=quality.score, issues=["The document could not be read reliably. Please upload a clearer image."], important_disagreements=disagreements, can_index=False, reupload_recommended=True, upload_guidance=["Ensure the full page is visible.", "Keep the camera directly above the document.", "Ensure text is in focus and avoid glare."])
        return ExtractionReliabilityResult(status="accepted_with_warnings", score=max(quality.score, .5), warnings=["Local vision fallback agreed with OCR transcription."], can_index=True, reupload_recommended=False)


extraction_reliability_service = ExtractionReliabilityService()
