"""Text-based local PDF extraction; OCR is intentionally outside this parser."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.documents.parsers.text_parser import normalize_text


class PdfExtractionError(Exception):
    """Raised when a PDF is corrupt, encrypted, or unreadable locally."""


def extract_text(content: bytes) -> tuple[str, int]:
    """Extract ordered page text and count pages from a validated PDF.

    Sparse output is deliberately returned to DocumentService, which marks it
    `ocr_required` instead of falsely claiming scanned text was extracted.
    """
    try:
        reader = PdfReader(BytesIO(content))
        # Encrypted PDFs are not bypassed; Phase 2 has no password workflow.
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PdfExtractionError("The PDF is encrypted and cannot be read.")
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return normalize_text(text), len(reader.pages)
    except PdfExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as error:
        raise PdfExtractionError("The PDF is corrupt or unreadable.") from error
