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


def test_vision_prompt_forbids_speculative_identifiers(monkeypatch, tmp_path) -> None:
    """Technical-image answers must not turn blurry marks into guessed labels."""
    from app.services.multimodal import vision_service as module
    from app.schemas.enums import FileType

    class Metadata: file_type = FileType.PNG
    class Model: ollama_model = "local-vision"
    captured: dict[str, str] = {}
    (tmp_path / "image-id.png").write_bytes(b"controlled image")
    monkeypatch.setattr(module.document_service, "get_metadata", lambda _: Metadata())
    monkeypatch.setattr(module.document_service, "files_directory", tmp_path)
    monkeypatch.setattr(module.model_manager, "select", lambda _: (Model(), None, None))
    monkeypatch.setattr(module.ollama_service, "vision_with_model", lambda _model, prompt, _bytes: captured.setdefault("prompt", prompt) or "local")

    VisionService().analyze("image-id", "List identifiers.")

    assert "Do not infer, complete, or invent identifiers" in captured["prompt"]
    assert "write [UNCERTAIN] instead" in captured["prompt"]
