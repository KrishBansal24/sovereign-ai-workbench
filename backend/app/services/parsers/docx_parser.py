"""Local DOCX text extraction."""

from io import BytesIO
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.services.parsers.text_parser import normalize_text


class DocxExtractionError(Exception):
    """A DOCX file could not be opened or parsed."""


def extract_text(content: bytes) -> str:
    try:
        document = Document(BytesIO(content))
    except (PackageNotFoundError, BadZipFile, ValueError, KeyError) as error:
        raise DocxExtractionError("The DOCX file is malformed or unreadable.") from error

    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append("\t".join(cells))
    return normalize_text("\n\n".join(parts))
