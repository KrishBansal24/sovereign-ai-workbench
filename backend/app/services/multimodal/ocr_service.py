"""Local OCR abstraction using Tesseract for controlled images and PDFs."""

import time
from io import BytesIO
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.multimodal.ocr_quality_service import OCRQualityResult, ocr_quality_service


class OCRUnavailableError(Exception):
    """Raised when local Tesseract or a required local renderer is unavailable."""


class OCRProcessingError(Exception):
    """Raised when controlled media cannot be OCR processed locally."""


class OCRPage(BaseModel):
    """OCR text associated with one one-indexed source page."""

    page_number: int
    text: str


class OCRResult(BaseModel):
    """Structured local OCR output retained as data, never instructions."""

    text: str
    pages: list[OCRPage]
    engine: Literal["tesseract"] = "tesseract"
    processing_time_ms: float
    warnings: list[str] = Field(default_factory=list)
    extraction_method: str = "ocr"
    quality: OCRQualityResult | None = None


class OCRService:
    """OCR application-owned bytes with replaceable local-engine integration."""

    @staticmethod
    def _normalize_ocr_text(raw: object) -> str:
        """Narrow third-party OCR output to str at the service boundary."""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, (bytes, bytearray)):
            return raw.decode("utf-8", errors="replace")
        raise OCRProcessingError(
            f"OCR engine returned unexpected type {type(raw).__name__}; expected str."
        )

    def image(self, content: bytes) -> OCRResult:
        """Extract text from validated image bytes through local Tesseract."""
        started_at = time.perf_counter()
        try:
            from PIL import Image, ImageOps
            import pytesseract
            # SECURITY: the executable location comes from trusted local
            # settings, never an API request or uploaded document metadata.
            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            image = Image.open(BytesIO(content))
            image = ImageOps.exif_transpose(image)
            if image.width * image.height > settings.image_max_pixels:
                raise OCRProcessingError("The image is too large to process safely.")
            raw_text = pytesseract.image_to_string(image)
        except ImportError as error:
            raise OCRUnavailableError("Local OCR dependencies are unavailable.") from error
        except Exception as error:
            raise OCRProcessingError("The image could not be OCR processed.") from error
        best_text: str = self._normalize_ocr_text(raw_text)
        method = "ocr"
        quality = ocr_quality_service.assess_text(best_text)
        if quality.requires_retry and settings.ocr_max_attempts > 1:
            retry_raw = pytesseract.image_to_string(Image.open(BytesIO(ocr_quality_service.preprocess(content))))
            retry_text: str = self._normalize_ocr_text(retry_raw)
            retry_quality = ocr_quality_service.assess_text(retry_text)
            if retry_quality.score > quality.score:
                best_text, quality, method = retry_text, retry_quality, "ocr_preprocessed"
        return OCRResult(text=best_text, pages=[OCRPage(page_number=1, text=best_text)], processing_time_ms=(time.perf_counter() - started_at) * 1_000, warnings=quality.reasons, extraction_method=method, quality=quality)

    def pdf(self, content: bytes, page_numbers: list[int] | None = None) -> OCRResult:
        """Render validated PDF pages locally and OCR them without cloud services."""
        started_at = time.perf_counter()
        try:
            import fitz
            document = fitz.open(stream=content, filetype="pdf")
            requested = page_numbers or list(range(1, len(document) + 1))
            if len(requested) > settings.ocr_max_pages:
                raise OCRProcessingError("The PDF has more OCR-required pages than the configured safety limit.")
            if any(number < 1 or number > len(document) for number in requested):
                raise OCRProcessingError("Requested PDF page is unavailable.")
            pages = [OCRPage(page_number=number, text=self.image(document[number - 1].get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")).text) for number in requested]
        except OCRProcessingError:
            raise
        except ImportError as error:
            raise OCRUnavailableError("Local PDF rendering dependency is unavailable.") from error
        except Exception as error:
            raise OCRProcessingError("The PDF could not be rendered for OCR.") from error
        text = "\n\n".join(page.text for page in pages)
        return OCRResult(text=text, pages=pages, processing_time_ms=(time.perf_counter() - started_at) * 1_000, warnings=[] if text.strip() else ["No text detected."])


ocr_service = OCRService()
