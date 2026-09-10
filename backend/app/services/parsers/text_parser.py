"""Conservative local TXT decoding and normalization for DocumentService."""


def normalize_text(text: str) -> str:
    """Normalize line endings and remove null characters without rewriting content."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")


def extract_text(content: bytes) -> str:
    """Decode common text encodings and fall back safely on malformed bytes."""
    # Try common industrial-document encodings before replacement decoding.
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return normalize_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(content.decode("utf-8", errors="replace"))
