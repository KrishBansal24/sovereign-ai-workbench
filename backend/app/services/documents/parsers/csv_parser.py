"""Bounded CSV-to-text extraction for RAG; original CSV bytes remain authoritative."""
import csv
from io import StringIO

from app.services.documents.parsers.text_parser import extract_text


def extract_csv(content: bytes, max_rows: int = 1000) -> tuple[str, dict[str, object]]:
    text = extract_text(content)
    try:
        sample = text[:8192]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        reader = csv.reader(StringIO(text), dialect)
        rows = list(reader)
    except (csv.Error, UnicodeError) as error:
        raise ValueError("The CSV file could not be parsed safely.") from error
    if not rows or not rows[0]:
        raise ValueError("The CSV file has no header row.")
    header, body = rows[0], rows[1:]
    preview = body[:max_rows]
    representation = [f"CSV DATASET\nCOLUMNS: {', '.join(header)}\nROWS: {len(body)}\n", "ROWS:"]
    representation.extend(" | ".join(cell for cell in row) for row in preview)
    if len(body) > max_rows: representation.append(f"[Preview limited to first {max_rows} rows]")
    return "\n".join(representation), {"row_count": len(body), "column_count": len(header), "columns": header, "delimiter": dialect.delimiter, "preview_rows": len(preview)}
