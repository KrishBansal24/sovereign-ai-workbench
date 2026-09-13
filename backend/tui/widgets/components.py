"""Reusable generic widgets and modals for the TUI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Select, Static, TextArea

from tui.constants import TYPE_LABELS
from tui.services.file_ingest import FolderScan


class PageHeader(Static):
    def __init__(self, title: str, description: str, next_step: str = "") -> None:
        super().__init__(f"[b]{title.upper()}[/b]\n{description}" + (f"\n[dim]Next: {next_step}[/dim]" if next_step else ""), classes="page-header")


class ResultPanel(Static):
    def __init__(self, empty: str, id: str) -> None:
        super().__init__(f"[dim]{empty}[/dim]", id=id, classes="result-panel")


class UploadModal(ModalScreen[dict[str, Any] | None]):
    def __init__(self, folder: bool = False) -> None:
        super().__init__()
        self.folder = folder

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield PageHeader("Upload Folder" if self.folder else "Upload File", "Files are opened here and sent as controlled multipart bytes.")
            yield Input(placeholder="Folder path (quotes and spaces are supported)" if self.folder else "File path (quotes and spaces are supported)", id="location")
            if self.folder:
                yield Checkbox("Include subfolders", value=True, id="recursive")
                yield Checkbox("Add ready documents to Knowledge after processing", id="index-after")
            with Horizontal(classes="actions"):
                yield Button("Scan folder" if self.folder else "Upload file", id="confirm", variant="primary")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss({"path": self.query_one("#location", Input).value.strip(), "folder": self.folder, "recursive": self.query_one("#recursive", Checkbox).value if self.folder else False, "index_after": self.query_one("#index-after", Checkbox).value if self.folder else False})

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)


class FolderPreviewModal(ModalScreen[bool | None]):
    """Show a name-first folder preview before multipart upload begins."""

    def __init__(self, scan: FolderScan) -> None:
        super().__init__()
        self.scan = scan

    def compose(self) -> ComposeResult:
        preview = "\n".join(
            f"• {path.name} — {TYPE_LABELS.get(path.suffix.lower().lstrip('.'), path.suffix.lstrip('.').upper())}"
            for path in self.scan.files[:5]
        )
        remainder = len(self.scan.files) - 5
        if remainder > 0:
            preview += f"\n[dim]… and {remainder} more file(s)[/dim]"
        with Container(classes="modal-card"):
            yield PageHeader("Folder Preview", "Review selected files before they are opened and uploaded locally.")
            yield Static(self.scan.summary + f"\n\n[b]FILES TO UPLOAD[/b]\n{preview}", classes="result-panel")
            with Horizontal(classes="actions"):
                yield Button(f"Upload {len(self.scan.files)} files", id="upload-folder-preview", variant="primary")
                yield Button("Cancel", id="cancel-folder-preview")

    @on(Button.Pressed, "#upload-folder-preview")
    def upload(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-folder-preview")
    def cancel(self) -> None:
        self.dismiss(None)


class DeliverableModal(ModalScreen[dict[str, str] | None]):
    def __init__(self, kind: str | None = None) -> None:
        super().__init__()
        self.kind = kind

    def compose(self) -> ComposeResult:
        with Container(classes="modal-card"):
            yield PageHeader("Create Deliverable", "Create a locally validated report, workbook, presentation, PDF, or chart.")
            yield Select((("Excel workbook", "xlsx"), ("Word report", "docx"), ("PowerPoint summary", "pptx"), ("PDF report", "pdf"), ("Chart", "chart")), value=self.kind or "xlsx", id="kind")
            yield Input(placeholder="Title, e.g. Maintenance Analysis", id="title")
            yield TextArea("", id="description")
            with Horizontal(classes="actions"):
                yield Button("Create validated file", id="create", variant="primary")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#create")
    def create(self) -> None:
        self.dismiss({"kind": str(self.query_one("#kind", Select).value), "title": self.query_one("#title", Input).value.strip() or "Sovereign Analysis", "description": self.query_one("#description", TextArea).text.strip()})

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)
