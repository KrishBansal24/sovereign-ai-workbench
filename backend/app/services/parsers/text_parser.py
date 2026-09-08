"""Plain-text parsing with conservative normalization."""


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")


def extract_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return normalize_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(content.decode("utf-8", errors="replace"))
