#!/usr/bin/env python
"""TEMPORARY DEVELOPMENT UTILITY — DO NOT USE IN PRODUCTION — DO NOT COMMIT.

Print and optionally reset only project-managed runtime data for a clean local
verification run. It is deliberately not imported by FastAPI or exposed as an
API endpoint. Stop the backend before using it so in-memory vector/job state is
also reset by the next process start.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
forbidden_roots = {REPOSITORY_ROOT.resolve(), BACKEND_ROOT.resolve(), Path.cwd().anchor}


def configured_data_root() -> Path:
    """Read the real local data directory through the application's settings."""
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.config import settings

    return settings.data_directory.resolve()


def require_safe_target(target: Path, data_root: Path) -> Path:
    """Reject every path outside the configured runtime-data directory."""
    resolved = target.resolve()
    if resolved in forbidden_roots or resolved == data_root or data_root not in resolved.parents:
        raise RuntimeError(f"Unsafe cleanup target rejected: {target.name}")
    return resolved


def child_files(directory: Path) -> list[Path]:
    """List immediate generated files while retaining the managed directory."""
    return list(directory.iterdir()) if directory.exists() else []


def describe(data_root: Path) -> tuple[list[Path], list[Path]]:
    """Derive cleanup targets from the current document/vector-store layout."""
    documents = data_root / "documents"
    knowledge = data_root / "knowledge"
    files = child_files(documents / "files")
    texts = child_files(documents / "texts")
    artifacts = [*files, *texts]
    # metadata.json contains document records, user confirmations, and job IDs.
    metadata = documents / "metadata.json"
    if metadata.exists():
        artifacts.append(metadata)
    knowledge_files = [path for path in child_files(knowledge) if path.name in {"index.faiss", "metadata.json", "vectors.npy"}]
    return artifacts, knowledge_files


def delete_items(items: Iterable[Path], data_root: Path) -> tuple[int, list[str]]:
    """Delete verified generated items and report failures without hiding them."""
    deleted = 0
    failures: list[str] = []
    for item in items:
        try:
            safe_item = require_safe_target(item, data_root)
            if safe_item.is_dir():
                shutil.rmtree(safe_item)
            else:
                safe_item.unlink(missing_ok=True)
            deleted += 1
        except OSError:
            failures.append(item.name)
    return deleted, failures


def initialize_empty_metadata(data_root: Path) -> None:
    """Restore the document metadata file expected by DocumentService."""
    documents = data_root / "documents"
    (documents / "files").mkdir(parents=True, exist_ok=True)
    (documents / "texts").mkdir(parents=True, exist_ok=True)
    (documents / "metadata.json").write_text("{}\n", encoding="utf-8")
    (data_root / "knowledge").mkdir(parents=True, exist_ok=True)


def main() -> int:
    """Show a dry-run inventory, require consent, then reset generated data."""
    parser = argparse.ArgumentParser(description="Reset Sovereign AI Workbench development runtime data.")
    parser.add_argument("--dry-run", action="store_true", help="Show targets only; do not prompt or delete.")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive prompt after development safety checks.")
    args = parser.parse_args()
    if (Path.cwd() / ".git").resolve() != (REPOSITORY_ROOT / ".git").resolve():
        print("ABORT: run this script from the repository root.")
        return 2
    if __import__("os").getenv("APP_ENV", "").lower() in {"prod", "production"}:
        print("ABORT: this temporary utility refuses APP_ENV=production.")
        return 2
    data_root = configured_data_root()
    if data_root.parent != BACKEND_ROOT.resolve() or not data_root.exists():
        print("ABORT: configured data root is not the expected local backend/data directory.")
        return 2
    artifacts, knowledge_files = describe(data_root)
    print("Sovereign AI Workbench Development Data Reset\n")
    print(f"Configured data root: {data_root.relative_to(REPOSITORY_ROOT)}")
    print(f"Uploaded/original files: {sum(1 for item in artifacts if item.parent.name == 'files')}")
    print(f"Extracted OCR/text files: {sum(1 for item in artifacts if item.parent.name == 'texts')}")
    print(f"Document metadata/confirmations: {'present' if (data_root / 'documents' / 'metadata.json').exists() else 'absent'}")
    print(f"Knowledge/FAISS artifacts: {len(knowledge_files)}")
    print("Background jobs: in memory only; restart the backend to clear them.")
    print("Database: none configured. Audit logs: no project-managed persisted audit-log directory found.\n")
    print("Files scheduled for cleanup:")
    for item in [*artifacts, *knowledge_files]:
        print(f"- {item.relative_to(REPOSITORY_ROOT)}")
    print("\nProtected: source, tests, docs, .env files, venv, Git data, models, and all configuration.")
    if args.dry_run:
        print("\nDry run complete. No files have been deleted.")
        return 0
    if not args.yes and input("\nProceed with cleanup? [y/N]: ").strip().lower() not in {"y", "yes"}:
        print("No files have been deleted.")
        return 0
    deleted, failures = delete_items([*artifacts, *knowledge_files], data_root)
    initialize_empty_metadata(data_root)
    print(f"\nCleanup completed. Deleted {deleted} generated artifacts.")
    if failures:
        print("FAILED:\n" + "\n".join(failures))
        return 1
    remaining = describe(data_root)
    print(f"Verification: upload storage empty={not any((data_root / 'documents' / 'files').iterdir())}; text storage empty={not any((data_root / 'documents' / 'texts').iterdir())}; knowledge artifacts={len(remaining[1])}.")
    print("Development environment is ready for clean verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
