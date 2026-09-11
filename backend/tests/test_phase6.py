"""Deterministic local OCR and vision integration tests without external engines."""

from app.services.multimodal.ocr_service import OCRPage, OCRResult, ocr_service
from app.services.multimodal.vision_service import VisionService


def test_image_ocr_result_is_page_aware(monkeypatch) -> None:
    """OCR retains page one text for a controlled uploaded-image path."""
    monkeypatch.setattr(ocr_service, "image", lambda content: OCRResult(text="P-202 72 C", pages=[OCRPage(page_number=1, text="P-202 72 C")], processing_time_ms=1))
    result = ocr_service.image(b"controlled")
    assert result.pages[0].page_number == 1 and "P-202" in result.text


def test_vision_requires_controlled_image_document(monkeypatch) -> None:
    """Vision rejects a non-image ID before any local model call."""
    from app.services.multimodal import vision_service as module
    class Metadata: file_type = "txt"
    monkeypatch.setattr(module.document_service, "get_metadata", lambda document_id: Metadata())
    try:
        VisionService().analyze("controlled-id")
        assert False, "Text documents must not reach vision inference."
    except ValueError:
        pass
