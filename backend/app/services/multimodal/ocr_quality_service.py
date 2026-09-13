"""Local heuristic image/OCR quality assessment and non-destructive preprocessing."""

from io import BytesIO
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field


QualityStatus = Literal["accepted", "accepted_with_warnings", "review_required", "reupload_required"]


class ImageQualityResult(BaseModel):
    """Heuristic image readiness indicators; values are not guarantees."""

    status: Literal["good", "improvable", "poor"]
    issues: list[str] = Field(default_factory=list)
    width: int
    height: int
    blur_score: float
    contrast_score: float
    preprocessing_recommended: bool


class OCRQualityResult(BaseModel):
    """Deterministic trust assessment for untrusted OCR text."""

    status: QualityStatus
    score: float
    reasons: list[str]
    extracted_character_count: int
    suspicious_character_ratio: float
    requires_retry: bool
    requires_review: bool


class OCRQualityService:
    """Assess controlled images/text and make bounded preprocessing derivatives."""

    def assess_image(self, content: bytes) -> ImageQualityResult:
        """Measure basic resolution, sharpness, and contrast heuristics locally."""
        from PIL import Image
        image = Image.open(BytesIO(content)).convert("L")
        values = np.asarray(image, dtype=np.float32)
        blur = float(np.var(np.diff(values, axis=0)) + np.var(np.diff(values, axis=1)))
        contrast = float(np.std(values))
        issues: list[str] = []
        if image.width < 800 or image.height < 600: issues.append("Resolution is low.")
        if blur < 80: issues.append("Image may be blurred.")
        if contrast < 25: issues.append("Image has low contrast.")
        status: Literal["good", "improvable", "poor"] = "poor" if len(issues) >= 2 else ("improvable" if issues else "good")
        return ImageQualityResult(status=status, issues=issues, width=image.width, height=image.height, blur_score=blur, contrast_score=contrast, preprocessing_recommended=bool(issues))

    def preprocess(self, content: bytes) -> bytes:
        """Create an in-memory grayscale, contrast-enhanced, enlarged derivative."""
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        image = Image.open(BytesIO(content))
        image = ImageOps.exif_transpose(image).convert("L")
        image = ImageEnhance.Contrast(image).enhance(1.8)
        image = image.filter(ImageFilter.SHARPEN)
        if max(image.size) < 1600: image = image.resize((image.width * 2, image.height * 2))
        output = BytesIO(); image.save(output, format="PNG")
        return output.getvalue()

    def assess_text(self, text: str) -> OCRQualityResult:
        """Reject empty/gibberish-like output without guessing technical values."""
        stripped = text.strip(); count = len(stripped)
        suspicious = sum(not (character.isalnum() or character.isspace() or character in ".,:;/-()[]") for character in stripped)
        ratio = suspicious / max(count, 1)
        reasons: list[str] = []
        if count < 20: reasons.append("Too little readable text was detected.")
        if ratio > 0.2: reasons.append("OCR output contains excessive unrecognized symbols.")
        score = max(0.0, min(1.0, (min(count / 100, 1) * 0.7) + ((1 - ratio) * 0.3)))
        status: QualityStatus = "accepted" if score >= .75 else ("review_required" if score >= .35 else "reupload_required")
        return OCRQualityResult(status=status, score=score, reasons=reasons, extracted_character_count=count, suspicious_character_ratio=ratio, requires_retry=status != "accepted", requires_review=status in {"review_required", "reupload_required"})


ocr_quality_service = OCRQualityService()
