"""Text-based local PDF extraction; OCR is intentionally outside this parser."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.documents.parsers.text_parser import normalize_text
from app.core.config import settings
from dataclasses import dataclass


class PdfExtractionError(Exception):
    """Raised when a PDF is corrupt, encrypted, or unreadable locally."""


@dataclass(frozen=True)
class PdfPageExtraction:
    """Page-local embedded text decision used to avoid unnecessary OCR."""
    page_number: int
    text: str
    usable: bool


def extract_pages(content: bytes) -> list[PdfPageExtraction]:
    """Read embedded text per page without treating a mixed PDF as homogeneous."""
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PdfExtractionError("The PDF is password protected and cannot be read.")
        if not reader.pages:
            raise PdfExtractionError("The PDF contains no pages.")
        if len(reader.pages) > settings.pdf_max_pages:
            raise PdfExtractionError("The PDF exceeds the configured page safety limit.")
        pages: list[PdfPageExtraction] = []
        for number, page in enumerate(reader.pages, 1):
            text = normalize_text(page.extract_text() or "")
            printable = sum(character.isprintable() or character.isspace() for character in text) / max(len(text), 1)
            words = len(text.split())
            usable = len(text.strip()) >= 20 and words >= 3 and printable >= .85
            pages.append(PdfPageExtraction(number, text, usable))
        return pages
    except PdfExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as error:
        raise PdfExtractionError("The PDF is corrupt or unreadable.") from error


def extract_text(content: bytes) -> tuple[str, int]:
    """Extract ordered page text and count pages from a validated PDF.

    Sparse output is deliberately returned to DocumentService, which marks it
    `ocr_required` instead of falsely claiming scanned text was extracted.
    """
    try:
        pages = extract_pages(content)
        return normalize_text("\n\n".join(page.text for page in pages)), len(pages)
    except PdfExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError) as error:
        raise PdfExtractionError("The PDF is corrupt or unreadable.") from error
