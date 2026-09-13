"""One authoritative batch-progress state; rendering never fabricates outcomes."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter


@dataclass
class BatchItem:
    path: Path
    status: str = "queued"
    reason: str | None = None


@dataclass
class BatchProgress:
    title: str
    items: list[BatchItem]
    current: str | None = None
    stage: str = "Queued"
    history: list[str] = field(default_factory=list)

    def set_current(self, item: BatchItem, status: str, stage: str, reason: str | None = None) -> None:
        self.current, self.stage = item.path.name, stage
        item.status, item.reason = status, reason
        self.history.append(f"{item.path.name}: {status}")

    @property
    def counts(self) -> Counter[str]: return Counter(item.status for item in self.items)
    @property
    def total(self) -> int: return len(self.items)
    @property
    def processed(self) -> int: return self.total - self.counts["queued"] - self.counts["uploading"]
    @property
    def failed(self) -> list[BatchItem]: return [item for item in self.items if item.status == "failed"]

    def render(self) -> str:
        counts = self.counts; remaining = counts["queued"] + counts["uploading"]
        lines = [f"[b]{self.title.upper()}[/b]", f"Processed: {self.processed} / {self.total}    Remaining: {remaining}", f"Uploaded: {counts['uploaded']}    Processing: {counts['processing']}    Failed: {counts['failed']}    Skipped: {counts['skipped']}    Duplicates: {counts['duplicate']}"]
        if self.current: lines.extend(["", f"Current: {self.current}", f"Stage: {self.stage}"])
        visible = self.items[-12:]
        if visible:
            lines.extend(["", "[b]ITEMS[/b]"])
            symbols = {"uploaded": "✓", "failed": "×", "queued": "○", "uploading": "…", "processing": "…", "skipped": "–", "duplicate": "↷"}
            lines.extend(f"{symbols.get(item.status, '•')} {item.path.name}  {item.status.title()}{': ' + item.reason if item.reason else ''}" for item in visible)
        return "\n".join(lines)
