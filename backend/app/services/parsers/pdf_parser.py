"""Text-based PDF extraction. OCR is deliberately out of scope for Phase 2."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.parsers.text_parser import normalize_text


class PdfExtractionError(Exception):
    """A PDF file could not be opened or read."""


def extract_text(content: bytes) -> tuple[str, int]:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PdfExtractionError("The PDF is encrypted and cannot be read.")
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return normalize_text(text), len(reader.pages)
    except PdfExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as error:
        raise PdfExtractionError("The PDF is corrupt or unreadable.") from error
