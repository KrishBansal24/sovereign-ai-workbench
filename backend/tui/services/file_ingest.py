"""Client-side safe file and folder selection for multipart ingestion."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".py", ".md", ".csv", ".xlsx", ".docx", ".png", ".jpg", ".jpeg"}
SKIP_DIRECTORIES = {".git", "node_modules", "venv", ".venv", "__pycache__"}


@dataclass(frozen=True)
class FolderScan:
    root: Path
    files: tuple[Path, ...]
    skipped_hidden: int
    skipped_unsupported: int
    skipped_links: int
    total_bytes: int
    types: dict[str, int]

    @property
    def summary(self) -> str:
        types = ", ".join(f"{kind.upper()}: {count}" for kind, count in sorted(self.types.items())) or "none"
        return f"Folder scan: {self.root.name}\nSupported files: {len(self.files)} · Size: {self.total_bytes / 1_048_576:.1f} MB\nSkipped: {self.skipped_hidden} hidden, {self.skipped_unsupported} unsupported, {self.skipped_links} links\nTypes: {types}"


def normalize_path(value: str) -> Path:
    """Accept a terminal-dropped quoted path without shell expansion."""
    return Path(value.strip().strip('"').strip("'"))


def scan_folder(value: str, *, recursive: bool = True, max_files: int = 500) -> FolderScan:
    """Safely inspect a human-selected folder without following symlinks."""
    root = normalize_path(value)
    if not root.is_dir(): raise ValueError("The selected folder does not exist or is not a directory.")
    files: list[Path] = []; hidden = unsupported = links = 0; total = 0; types: Counter[str] = Counter()
    iterator = root.rglob("*") if recursive else root.glob("*")
    for path in iterator:
        relative = path.relative_to(root)
        if any(part in SKIP_DIRECTORIES or part.startswith(".") for part in relative.parts):
            hidden += 1; continue
        if path.is_symlink(): links += 1; continue
        if not path.is_file(): continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            unsupported += 1; continue
        if len(files) >= max_files: break
        try: size = path.stat().st_size
        except OSError: continue
        files.append(path); total += size; types[path.suffix.lower().lstrip(".")] += 1
    return FolderScan(root, tuple(files), hidden, unsupported, links, total, dict(types))
