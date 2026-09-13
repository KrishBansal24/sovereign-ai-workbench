"""Product-focused Textual interface for the local Sovereign workbench."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Select, Static, TextArea

from tui.screens.command_palette import CommandModal
from tui.services.api_client import APIClient, BackendError
from tui.services.file_ingest import FolderScan, normalize_path, scan_folder
from tui.services.job_poller import poll_job
from tui.state.progress import BatchItem, BatchProgress
from tui.constants import ALL_NAV_KEYS, NAV, NAV_GROUPS, RELIABILITY, TYPE_LABELS
from tui.widgets.components import DeliverableModal, FolderPreviewModal, PageHeader, ResultPanel, UploadModal


def friendly(value: str) -> str:
    return Path(value).stem.replace("_", " ").replace("-", " ").title()


def job_name(job: dict[str, Any]) -> str:
    return job.get("display_name") or job.get("resource_name") or job.get("operation", "Task").replace("_", " ").title()


def agent_step_label(step: dict[str, Any]) -> str:
    """Render a safe trace label without exposing an empty tool value."""
    return str(step.get("tool") or ("Planning" if step.get("action") == "final" else "Local task"))


# Widgets and modals are in tui.widgets.components


class SovereignTUI(App[None]):
    """Presentation-only primary UI. FastAPI remains authoritative."""
    CSS_PATH = "styles/app.tcss"; TITLE = "Sovereign Terminal Workbench"
    BINDINGS = [Binding("ctrl+k", "command", "Commands"), Binding("f2", "command", "Commands", show=True), Binding("r", "refresh", "Refresh", show=True), Binding("q", "quit", "Quit", show=True), Binding("question_mark", "open_help", "Help", show=True)]

    def __init__(self) -> None:
        super().__init__(); self.client = APIClient(); self.current = "home"; self.documents: dict[str, dict[str, Any]] = {}; self.artifacts: dict[str, dict[str, Any]] = {}; self.indexed_ids: set[str] = set(); self.active_jobs: dict[str, dict[str, Any]] = {}; self.folder_scan: FolderScan | None = None; self.folder_index_after = False; self.folder_progress: BatchProgress | None = None; self.latest_analysis: dict[str, Any] | None = None; self.selected_document_id: str | None = None; self.knowledge_source_pages: dict[str, list[int]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="shell"):
            with Vertical(id="sidebar"):
                yield Static("SOVEREIGN AI", id="brand")
                for group_name, items in NAV_GROUPS:
                    yield Static(group_name, classes="nav-section")
                    for key, label in items:
                        shortcut = ""
                        try:
                            idx = [n[0] for n in NAV].index(key) + 1
                            if idx <= 9: shortcut = f" {idx} "
                        except ValueError:
                            pass
                        yield Button(f"{shortcut}{label}", id=f"nav-{key}", classes="nav")
            with Vertical(id="main"):
                yield Static("LOCAL  •  Connecting to backend…", id="status-bar")
                with VerticalScroll(id="workspace"):
                    for key in ALL_NAV_KEYS: yield Container(id=key, classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self._build_pages(); self.show_page("home"); self.refresh_backend()
    async def on_unmount(self) -> None: await self.client.close()

    def _build_pages(self) -> None:
        self.query_one("#home").mount(PageHeader("Sovereign AI", "Private AI workspace running entirely on this machine.", "Upload documents, add ready files to Knowledge, then ask a question."), ResultPanel("[#8B9DAA]Loading workspace…[/]", "home-summary"), Horizontal(Button("Ask Agent", id="home-agent", variant="primary"), Button("Upload Documents", id="home-upload"), Button("Add Ready to Knowledge", id="home-index"), Button("Analyze Data", id="home-data"), classes="actions"), ResultPanel("[#8B9DAA]Recent activity will appear here.[/]", "home-activity"))
        self.query_one("#agent").mount(PageHeader("Agent", "Ask Sovereign AI to investigate, calculate, analyze, or create using approved local tools.", "Describe the outcome you want; sources and generated files appear after execution."), TextArea("Find the recorded vibration readings for Pump P-101 and calculate their average.", id="agent-goal"), Static("Knowledge: loading…  •  Tools: approved local tools  •  Execution: bounded", id="agent-context", classes="context"), Button("Run task", id="run-agent", variant="primary"), ResultPanel("[#8B9DAA]Ask a task to receive an answer, sources, and a safe execution summary.[/]", "agent-result"))
        self.query_one("#documents").mount(PageHeader("Documents", "Your local document workspace.", "Upload files, review anything uncertain, then add ready documents to Knowledge."), Horizontal(Button("Upload files", id="upload-file", variant="primary"), Button("Upload folder", id="upload-folder"), Button("Add ready to Knowledge", id="index-all"), classes="actions"), Input(placeholder="Search documents by name", id="document-search"), Select((("All documents", "all"), ("Ready", "ready"), ("Needs review", "review"), ("Indexed", "indexed")), value="all", id="document-filter"), ResultPanel("[#8B9DAA][b]NO DOCUMENTS YET[/b]\n\nUpload a file or folder to begin building your local workspace.[/]", "document-list"), Select((), prompt="Select a document for details", id="document-picker"), Horizontal(Button("View details", id="document-details"), Button("Review OCR / Vision", id="document-vision"), Button("Add to Knowledge", id="document-index"), Button("Ask about this", id="document-ask"), Button("View extracted text", id="document-text"), classes="actions"), ResultPanel("[#8B9DAA][b]NO DOCUMENTS YET[/b]\n\nUpload a file or folder to begin building your local workspace.[/]", "documents-result"))
        self.query_one("#knowledge").mount(PageHeader("Knowledge", "Ask grounded questions across your indexed local documents.", "Ask a question first; use search to inspect matching evidence."), Static(id="knowledge-summary", classes="context"), Input(placeholder="What maintenance guidance is relevant to abnormal pump vibration?", id="knowledge-question"), Horizontal(Button("Ask Knowledge", id="knowledge-ask", variant="primary"), Button("Search evidence", id="knowledge-search"), Button("Add ready documents", id="knowledge-index"), classes="actions"), ResultPanel("[#8B9DAA][b]NO KNOWLEDGE SOURCES YET[/b]\n\nAdd ready documents from the Documents workspace to begin.[/]", "knowledge-result"))
        self.query_one("#knowledge").mount(Select((), prompt="Select a cited source to open", id="knowledge-source-picker"), Button("Open selected source", id="knowledge-open-source"))
        self.query_one("#vision").mount(PageHeader("OCR / Vision", "Analyze scanned documents, handwriting, and engineering imagery.", "Select an image or scanned document to inspect reliability and extracted evidence."), Select((), prompt="Select a document", id="vision-picker"), Horizontal(Button("Analyze", id="vision-analyze", variant="primary"), Button("Add to Knowledge", id="vision-index"), Button("View full text", id="vision-text"), classes="actions"), Input(placeholder="Optional question about this image", id="vision-question"), Button("Ask about image", id="vision-ask"), Container(id="confirmation-area"), ResultPanel("[#8B9DAA][b]NO DOCUMENT SELECTED[/b]\n\nChoose a document to begin OCR / Vision review.[/]", "vision-result"))
        self.query_one("#data").mount(PageHeader("Data Analysis", "Analyze local operational datasets using approved local tools.", "Select a dataset to begin."), Static("DATASET", classes="nav-section"), Select((), prompt="Select a CSV or Excel dataset", id="dataset-picker"), Static("ASK ABOUT YOUR DATA", classes="nav-section"), TextArea("Which asset has the highest average vibration?", id="data-question"), Button("Analyze with AI", id="data-ask-ai", variant="primary"), Static("────────────── OR USE STRUCTURED ANALYSIS ──────────────", classes="nav-section"), Static("OPERATION", classes="nav-section"), Select((("Summary statistics", "summary"), ("Highest / lowest / average", "statistics"), ("Average by category", "group_average"), ("Filter rows", "filter")), value="summary", id="analysis-operation"), Static("PARAMETERS", classes="nav-section"), Select((), prompt="Numeric column (Measure)", id="analysis-value"), Select((), prompt="Category column (Group by)", id="analysis-group"), Select((), prompt="Filter column (optional)", id="analysis-filter-column"), Input(placeholder="Filter value (optional)", id="analysis-filter-value"), Button("Run Analysis", id="run-analysis", variant="primary"), ResultPanel("[#8B9DAA][b]NO DATASETS YET[/b]\n\nUpload or select a CSV/XLSX dataset to begin analysis.[/]", "data-result"), Horizontal(Button("Create chart", id="analysis-chart"), Button("Export Excel", id="analysis-xlsx"), Button("Create report", id="analysis-report"), Button("Send to Agent", id="analysis-agent"), classes="actions"))
        self.query_one("#sandbox").mount(PageHeader("Python Workspace", "A deliberately technical, bounded local execution workspace.", "Run safe Python; results and any captured files remain backend-controlled."), TextArea("print(sum([4.2, 4.8, 5.0, 4.6]) / 4)", id="sandbox-code"), Button("Run Python", id="run-sandbox", variant="primary"), ResultPanel("[#8B9DAA]Run Python to see output and safe execution status.[/]", "sandbox-result"))
        self.query_one("#artifacts").mount(PageHeader("Artifacts", "Validated local reports, spreadsheets, presentations, PDFs, and charts.", "Create a deliverable from current analysis or save a validated file."), Horizontal(Button("Create deliverable", id="create-deliverable", variant="primary"), Button("Refresh library", id="refresh-artifacts"), classes="actions"), ResultPanel("[#8B9DAA][b]NO ARTIFACTS YET[/b]\n\nGenerated charts, spreadsheets, reports, and presentations will appear here.[/]", "artifact-list"), Select((), prompt="Select a generated file", id="artifact-picker"), Input(value="outputs\\", placeholder="Save destination, e.g. outputs\\report.xlsx", id="artifact-save-path"), Horizontal(Button("Save As", id="save-artifact", variant="primary"), Button("View details", id="artifact-details"), classes="actions"), ResultPanel("[#8B9DAA][b]NO ARTIFACTS YET[/b]\n\nGenerated charts, spreadsheets, reports, and presentations will appear here.[/]", "artifacts-result"))
        self.query_one("#jobs").mount(PageHeader("Jobs", "Track local uploads, analysis, and safe execution.", "Running, failed, and review-required work remains visible here."), Static(id="jobs-summary", classes="context"), ResultPanel("[#8B9DAA][b]NO RUNNING JOBS[/b]\n\nBackground processing activity will appear here.[/]", "jobs-list"), Select((), prompt="Select a task for live progress", id="job-picker"), Horizontal(Button("View live progress", id="poll-job", variant="primary"), Button("Refresh jobs", id="refresh-jobs"), Button("Open Documents", id="job-document"), classes="actions"), ResultPanel("[#8B9DAA][b]NO RUNNING JOBS[/b]\n\nBackground processing activity will appear here.[/]", "jobs-result"))
        self.query_one("#models").mount(PageHeader("Models", "Actual configured local models and availability.", "Model routing remains backend-managed."), Button("Refresh models", id="refresh-models"), ResultPanel("[#8B9DAA]Loading local model status…[/]", "models-result"))
        self.query_one("#settings").mount(PageHeader("Settings", "Safe interface and local connection information.", "Secrets and environment values are never displayed."), Static("[b]Backend[/b]\nhttp://127.0.0.1:8000  •  Local connection\n\n[b]Privacy[/b]\n[#3FB950]✓[/] Local backend\n[#3FB950]✓[/] Local model provider\n[#3FB950]✓[/] No cloud provider configured\n\n[b]Phase 7[/b]\nImplemented — waiting for user manual verification.", classes="settings-copy"))
        self.query_one("#help").mount(PageHeader("Help", "A private, local-first workflow.", "Start with documents, then Knowledge or Agent."), Static("[b]GETTING STARTED[/b]\n1. Upload documents or a folder\n2. Add ready files to Knowledge\n3. Ask Knowledge or Agent\n4. Analyze CSV/XLSX data\n5. Generate and save validated reports\n\n[b]KEYBOARD[/b]\nCtrl+K / F2 Commands\nR Refresh\n? Help\nEsc Close a dialog\nQ Quit when not editing\n\n[b]WORKFLOWS[/b]\nDocuments → OCR / Vision → Knowledge → Agent → Artifacts\nData → Analysis → Chart / Report\n\nThe Workbench manages internal identifiers automatically.", classes="help-copy"))

    def show_page(self, name: str) -> None:
        self.current = name
        for panel in self.query(".panel"): panel.display = panel.id == name
        self.query_one("#workspace", VerticalScroll).scroll_home(animate=False)
        if name == "models":
            self.load_models()
            
        try:
            if name == "agent": self.query_one("#agent-goal", TextArea).focus()
            elif name == "knowledge": self.query_one("#knowledge-question", Input).focus()
            elif name == "documents": self.query_one("#document-search", Input).focus()
            elif name == "sandbox": self.query_one("#sandbox-code", TextArea).focus()
        except Exception:
            pass
    def action_refresh(self) -> None: self.refresh_backend()
    def action_open_help(self) -> None: self.show_page("help")
    def action_command(self) -> None: self.push_screen(CommandModal(), self.run_command)
    def on_key(self, event: Any) -> None:
        if isinstance(self.focused, (Input, TextArea, Select)): return
        if event.key in {str(i) for i in range(1, 10)}: self.show_page(NAV[int(event.key) - 1][0]); event.stop()
    def run_command(self, command: str | None) -> None:
        if not command: return
        if command == "upload-file": self.open_upload(False)
        elif command == "upload-folder": self.open_upload(True)
        elif command == "index-all": self.index_all()
        elif command == "refresh": self.refresh_backend()
        else: self.show_page(command)

    @on(Button.Pressed)
    def buttons(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("nav-"): self.show_page(bid[4:]); return
        actions: dict[str, Any] = {"home-agent": lambda: self.show_page("agent"), "home-upload": lambda: self.open_upload(False), "home-index": self.index_all, "home-data": lambda: self.show_page("data"), "upload-file": lambda: self.open_upload(False), "upload-folder": lambda: self.open_upload(True), "index-all": self.index_all, "document-details": self.document_details, "document-vision": self.open_vision, "document-index": self.index_document, "document-ask": self.ask_document, "document-text": self.document_text, "knowledge-ask": self.knowledge_ask, "knowledge-search": self.knowledge_search, "knowledge-index": self.index_all, "knowledge-open-source": self.open_knowledge_source, "vision-analyze": self.vision_analyze, "vision-ask": self.vision_ask, "vision-index": self.index_document, "vision-text": self.vision_text, "run-analysis": self.run_analysis, "data-ask-ai": self.run_data_ask_ai, "analysis-chart": lambda: self.open_deliverable("chart"), "analysis-xlsx": lambda: self.open_deliverable("xlsx"), "analysis-report": lambda: self.open_deliverable("docx"), "analysis-agent": self.analysis_to_agent, "run-agent": self.run_agent, "run-sandbox": self.run_sandbox, "create-deliverable": lambda: self.open_deliverable(), "refresh-artifacts": self.load_artifacts, "save-artifact": self.save_artifact, "artifact-details": self.artifact_details, "poll-job": self.start_poll, "refresh-jobs": self.load_jobs, "job-document": lambda: self.show_page("documents"), "refresh-models": self.load_models, "confirm-extraction": self.confirm_extraction}
        if bid in actions: actions[bid]()

    @on(Input.Changed, "#document-search")
    @on(Select.Changed, "#document-filter")
    def document_filter_changed(self) -> None: self.render_documents()
    @on(Select.Changed, "#vision-picker")
    def vision_selected(self) -> None:
        selected = self.selected("#vision-picker")
        if selected:
            self.selected_document_id = selected
            self.render_confirmation(selected)
            self.update_document_actions()
    @on(Select.Changed, "#document-picker")
    def document_selected(self) -> None:
        selected = self.selected("#document-picker")
        if selected:
            self.selected_document_id = selected
            if self.documents[selected].get("file_type") in {"png", "jpg", "jpeg"}:
                self.query_one("#vision-picker", Select).value = selected
            self.update_document_actions()

    @on(Select.Changed, "#dataset-picker")
    def dataset_selected(self) -> None:
        selected = self.selected("#dataset-picker")
        columns: list[str] = []
        if selected and selected in self.documents:
            structured = self.documents[selected].get("structured_metadata", {})
            columns = structured.get("columns", [])
        
        col_options = [(c, c) for c in columns]
        self.query_one("#analysis-value", Select).set_options(col_options)
        self.query_one("#analysis-group", Select).set_options(col_options)
        self.query_one("#analysis-filter-column", Select).set_options(col_options)

    @on(Select.Changed, "#analysis-operation")
    def operation_selected(self) -> None:
        op = self.selected("#analysis-operation")
        self.query_one("#analysis-value", Select).disabled = False
        self.query_one("#analysis-group", Select).disabled = op not in {"group_average"}
        self.query_one("#analysis-filter-column", Select).disabled = op not in {"filter"}
        self.query_one("#analysis-filter-value", Input).disabled = op not in {"filter"}

    def update_document_actions(self) -> None:
        """Keep Knowledge actions aligned with backend-authoritative eligibility."""
        item = self.current_document()
        blocked = not item or not item.get("index_eligible", False)
        self.query_one("#document-index", Button).disabled = blocked
        self.query_one("#vision-index", Button).disabled = blocked
    def selected(self, selector: str) -> str | None:
        value = self.query_one(selector, Select).value
        return None if value is Select.BLANK else str(value)
    def result(self, selector: str, text: str) -> None: self.query_one(selector, Static).update(text)
    def error(self, selector: str, error: Exception) -> None: self.result(selector, f"[red][b]COULDN'T COMPLETE THAT[/b][/red]\n{error}\n\n[dim]The Workbench is still available. Retry when ready.[/dim]")

    @work(exclusive=False)
    async def refresh_backend(self) -> None:
        try:
            health, docs, artifacts, jobs, indexed = await self.client.health(), await self.client.documents(), await self.client.artifacts(), await self.client.jobs(), await self.client.indexed_documents()
            self.documents = {item["document_id"]: item for item in docs}; self.artifacts = {item["artifact_id"]: item for item in artifacts}; self.indexed_ids = {item["document_id"] for item in indexed}
            review = sum(not item.get("index_eligible", False) for item in docs); running = sum(item.get("status") in {"queued", "running"} for item in jobs)
            
            # Status Bar Update
            model_name = health.get("model", "unknown")
            backend_badge = "[#00D49D]● Backend[/]" if health.get("backend") == "online" else "[#F85149]● Backend Offline[/]"
            ollama_badge = "[#00D49D]● Ollama[/]" if health.get("ollama") == "available" else "[#F85149]● Ollama Unavailable[/]"
            
            self.query_one("#status-bar", Static).update(
                f"SOVEREIGN AI   [b]LOCAL / AIR-GAPPED[/b]   {backend_badge}   {ollama_badge}   [#8B9DAA]Model: {model_name}[/]   [#8B9DAA]Jobs: {running}[/]"
            )
            
            # Sidebar counts
            try:
                self.query_one("#nav-documents", Button).label = f" 4  Documents       {len(docs)}"
                self.query_one("#nav-artifacts", Button).label = f" 6  Artifacts       {len(artifacts)}"
                self.query_one("#nav-jobs", Button).label = f" 9  Jobs            {running if running else ''}".strip()
            except Exception:
                pass

            self.render_home(health, docs, artifacts, jobs); self.render_documents(); self.render_data_sources(); self.render_artifacts(); self.render_jobs(jobs); self.result("#knowledge-summary", f"{len(indexed)} documents indexed  •  {sum(item.get('index_eligible') and item['document_id'] not in self.indexed_ids for item in docs)} ready to add")
        except BackendError as exc:
            self.query_one("#status-bar", Static).update("SOVEREIGN AI   [b]LOCAL / AIR-GAPPED[/b]   [#F85149]● Backend Offline[/]   [#8B9DAA]Press R to retry[/]"); self.result("#home-summary", "[#F85149][b]BACKEND OFFLINE[/b][/]\nUnable to reach the local backend. Start FastAPI, then press R to reconnect.")

    def render_home(self, health: dict[str, Any], docs: list[dict[str, Any]], artifacts: list[dict[str, Any]], jobs: list[dict[str, Any]]) -> None:
        review = sum(not item.get("index_eligible", False) for item in docs)
        running = sum(item.get("status") in {"queued", "running"} for item in jobs)
        
        backend_status = "[#3FB950]✓ Backend[/]" if health.get("backend") == "online" else "[#F85149]✕ Backend[/]"
        ollama_status = "[#3FB950]✓ Ollama[/]" if health.get("ollama") == "available" else "[#F85149]✕ Ollama[/]"
        knowledge_status = "[#3FB950]✓ Knowledge[/]" if self.indexed_ids else "[#8B9DAA]○ Knowledge (empty)[/]"
        sandbox_status = "[#3FB950]✓ Sandbox[/]"
        
        model_name = health.get("model", "unknown")
        
        dashboard = (
            f"[b]LOCAL EXECUTION[/b]\n{backend_status}\n{ollama_status}\n{knowledge_status}\n{sandbox_status}\n\n"
            f"[b]ACTIVE MODEL[/b]\n[#00D49D]{model_name}[/]\n[#8B9DAA]Local reasoning model[/]\n\n"
            f"[b]WORKSPACE[/b]\n"
            f"Documents        {len(docs)}\n"
            f"Knowledge        {len(self.indexed_ids)}\n"
            f"Artifacts        {len(artifacts)}\n"
            f"Running Jobs     {running}"
        )
        self.result("#home-summary", dashboard)
        
        activity = [f"{'[#F85149]✕[/]' if job.get('status') == 'failed' else '[#D29922]![/]' if job.get('status') == 'waiting_for_user' else '[#3FB950]✓[/]'} {job_name(job)}\n  [#8B9DAA]{job.get('message', '')}[/]" for job in jobs[:5]]
        self.result("#home-activity", "[b]RECENT ACTIVITY[/b]\n\n" + ("\n\n".join(activity) if activity else "[#8B9DAA]Upload documents or run a task to begin.[/]"))

    def render_documents(self) -> None:
        query = self.query_one("#document-search", Input).value.lower(); state = self.selected("#document-filter") or "all"; items = list(self.documents.values())
        if query: items = [item for item in items if query in item["filename"].lower()]
        if state == "ready": items = [item for item in items if item.get("index_eligible")]
        elif state == "review": items = [item for item in items if not item.get("index_eligible")]
        elif state == "indexed": items = [item for item in items if item["document_id"] in self.indexed_ids]
        lines = ["[b]NAME                              TYPE       STATUS                    KNOWLEDGE[/b]"]
        for item in items:
            status = RELIABILITY.get(item.get("reliability_status", ""), "Processing"); knowledge = "Indexed" if item["document_id"] in self.indexed_ids else ("Ready" if item.get("index_eligible") else "Review first")
            lines.append(f"{friendly(item['filename'])[:32]:32}  {TYPE_LABELS.get(item['file_type'], item['file_type'].upper()):8}  {status[:24]:24}  {knowledge}")
        self.result("#document-list", "\n".join(lines) if len(lines) > 1 else "[dim]No documents match this view.[/dim]")
        options = [(f"{friendly(item['filename'])} • {RELIABILITY.get(item.get('reliability_status', ''), 'Processing')}", item["document_id"]) for item in items]
        vision_options = [option for option, item in zip(options, items) if item.get("file_type") in {"png", "jpg", "jpeg"}]
        self.query_one("#vision-picker", Select).set_options(vision_options); self.query_one("#document-picker", Select).set_options(options)
        self.result("#documents-result", f"{len(items)} file{'s' if len(items) != 1 else ''} shown. Select one in OCR / Vision to inspect details.")

    def render_data_sources(self) -> None:
        choices = [(f"{friendly(item['filename'])} • {item['file_type'].upper()}", f"document:{item['document_id']}") for item in self.documents.values() if item.get("file_type") in {"csv", "xlsx"}]
        choices += [(f"{friendly(item['filename'])} • generated {item.get('artifact_type', 'file')}", f"artifact:{item['artifact_id']}") for item in self.artifacts.values() if item["filename"].lower().endswith((".csv", ".xlsx"))]
        self.query_one("#dataset-picker", Select).set_options(choices)

    def render_artifacts(self) -> None:
        lines = ["[b]NAME                              TYPE            STATUS[/b]"]
        for item in self.artifacts.values(): lines.append(f"{friendly(item['filename'])[:32]:32}  {item.get('artifact_type', 'file').title()[:14]:14}  ✓ Validated")
        self.result("#artifact-list", "\n".join(lines) if len(lines) > 1 else "[dim]No generated files yet. Ask the Agent or create a deliverable.[/dim]")
        self.query_one("#artifact-picker", Select).set_options([(f"{friendly(item['filename'])} • Validated", item["artifact_id"]) for item in self.artifacts.values()])

    def render_jobs(self, jobs: list[dict[str, Any]]) -> None:
        counts = {state: sum(item.get("status") == state for item in jobs) for state in ("running", "queued", "waiting_for_user", "failed", "completed")}; self.result("#jobs-summary", f"Running {counts['running'] + counts['queued']}    Needs Input {counts['waiting_for_user']}    Failed {counts['failed']}    Completed {counts['completed']}")
        lines = ["[b]RECENT TASKS[/b]"]
        for job in jobs:
            marker = "●" if job.get("status") in {"running", "queued"} else "!" if job.get("status") == "waiting_for_user" else "✕" if job.get("status") == "failed" else "✓"; lines.append(f"{marker} {job_name(job)}\n  {job.get('message', '')}")
        self.result("#jobs-list", "\n".join(lines) if len(lines) > 1 else "[dim]No recent activity.[/dim]"); self.query_one("#job-picker", Select).set_options([(job_name(job), job["job_id"]) for job in jobs])

    def render_confirmation(self, document_id: str) -> None:
        area = self.query_one("#confirmation-area", Container); area.remove_children(); disagreements = self.documents.get(document_id, {}).get("extraction_disagreements", [])
        if disagreements:
            item = disagreements[0]; area.mount(Static(f"[yellow][b]REVIEW REQUIRED[/b][/yellow]\n{item.get('field_or_token', 'Technical value')}\nOCR: {item.get('ocr_value')}\nVision: {item.get('vision_value')}\nChoose which reading to keep.", classes="review-card"), Select((("Use OCR reading", "ocr"), ("Use vision reading", "vision"), ("Enter a manual value", "manual")), value="ocr", id="confirm-source"), Input(placeholder="Manual value (only if selected)", id="confirm-manual"), Button("Confirm reading", id="confirm-extraction", variant="primary"))

    def open_upload(self, folder: bool) -> None: self.push_screen(UploadModal(folder), self.after_upload)
    def after_upload(self, data: dict[str, Any] | None) -> None:
        if data and data.get("path"):
            if data["folder"]: self.scan_folder(data)
            else: self.upload_file(data["path"])

    @work(exclusive=False)
    async def upload_file(self, value: str) -> None:
        try:
            job = await self.client.upload(normalize_path(value)); self.show_page("documents"); self.result("#documents-result", "[b]UPLOADING FILE[/b]\nThe file was accepted and is being processed locally."); self.track(job.get("job_id"), "#documents-result")
        except (BackendError, OSError) as exc: self.error("#documents-result", exc)

    @work(exclusive=False)
    async def scan_folder(self, data: dict[str, Any]) -> None:
        try:
            self.folder_scan = scan_folder(data["path"], recursive=bool(data.get("recursive", True))); scan = self.folder_scan; self.show_page("documents")
            self.folder_index_after = bool(data.get("index_after"))
            self.result("#documents-result", f"[b]FOLDER SCANNED[/b]\n{len(scan.files)} supported files found • {scan.skipped_unsupported} unsupported skipped • {scan.skipped_hidden} hidden skipped • {scan.skipped_links} links skipped\n\nReview the file preview, then explicitly start upload.")
            self.push_screen(FolderPreviewModal(scan), self.after_folder_preview)
        except (ValueError, OSError) as exc: self.error("#documents-result", exc)

    def after_folder_preview(self, confirmed: bool | None) -> None:
        """Begin upload only after the user accepts the scanned-file preview."""
        if confirmed:
            self.upload_folder(self.folder_index_after)

    @work(exclusive=False)
    async def upload_folder(self, index_after: bool = False) -> None:
        if not self.folder_scan or not self.folder_scan.files: return
        self.folder_progress = BatchProgress(f"Uploading dataset — {self.folder_scan.root.name}", [BatchItem(path) for path in self.folder_scan.files])
        for item in self.folder_progress.items:
            self.folder_progress.set_current(item, "uploading", "Uploading"); self.result("#documents-result", self.folder_progress.render())
            try:
                # Folder uploads have their own real item-state display. Starting a
                # polling worker (and a full workspace refresh) for every file
                # causes needless request storms on large folders; Jobs remains
                # the dedicated live backend-progress view after submission.
                await self.client.upload(item.path)
                self.folder_progress.set_current(item, "uploaded", "Uploaded; processing continues")
            except (BackendError, OSError) as exc: self.folder_progress.set_current(item, "failed", "Upload failed", str(exc))
        self.folder_progress.current = None; self.folder_progress.stage = "Upload complete"; self.result("#documents-result", self.folder_progress.render() + "\n\n[b]UPLOAD COMPLETE[/b]\nBackend processing continues in Jobs. Failed items remain visible in this summary."); self.refresh_backend()
        if index_after: self.index_all()

    def current_document(self) -> dict[str, Any] | None: return self.documents.get(self.selected_document_id or "")
    def document_details(self) -> None:
        item = self.current_document()
        if not item: self.notify("Select a document in OCR / Vision first.", severity="warning"); return
        warnings = "\n".join(f"• {value}" for value in item.get("extraction_warnings", [])) or "None"
        extra = item.get("structured_metadata", {}); facts = "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in extra.items() if key in {"line_count", "row_count", "column_count", "section_count", "functions", "classes", "columns"})
        recommendation = "Re-upload a clearer scan before adding this document to Knowledge." if not item.get("index_eligible", False) else "This document is eligible for local Knowledge indexing."
        self.result("#documents-result", f"[b]{friendly(item['filename'])}[/b]\n{TYPE_LABELS.get(item['file_type'], item['file_type'].upper())} • {RELIABILITY.get(item.get('reliability_status', ''), 'Processing')}\n\n[b]INFORMATION[/b]\n{facts or 'Text extraction available.'}\n\n[b]PROCESSING[/b]\nPages: {item.get('page_count') or '—'}\nWarnings:\n{warnings}\n\n[b]NEXT ACTION[/b]\n{recommendation}\n\n[dim]Original filename: {item['filename']}[/dim]")
    def open_vision(self) -> None: self.show_page("vision")
    def ask_document(self) -> None:
        item = self.current_document()
        if not item: self.notify("Select a document first.", severity="warning"); return
        self.show_page("knowledge"); self.query_one("#knowledge-question", Input).value = f"What does {friendly(item['filename'])} say about "

    def open_knowledge_source(self) -> None:
        """Open a cited source in Documents without exposing its internal ID."""
        document_id = self.selected("#knowledge-source-picker")
        if not document_id:
            self.notify("Select a cited source first.", severity="warning")
            return
        if document_id not in self.documents:
            self.notify("That cited source is no longer available locally.", severity="warning")
            return
        self.selected_document_id = document_id
        self.query_one("#document-picker", Select).value = document_id
        self.show_page("documents")
        self.document_details()
        pages = self.knowledge_source_pages.get(document_id, [])
        if pages:
            panel = self.query_one("#documents-result", Static)
            panel.update(f"{panel.renderable}\n\n[b]KNOWLEDGE CITATION[/b]\nPages: {', '.join(str(page) for page in pages)}")

    @work(exclusive=False)
    async def document_text(self) -> None:
        item = self.current_document()
        if not item: self.notify("Select a document first.", severity="warning"); return
        try: payload = await self.client.document_text(item["document_id"]); self.result("#documents-result", f"[b]EXTRACTED TEXT — {friendly(item['filename'])}[/b]\n{payload.get('text', '')[:8000] or 'No extracted text is available.'}")
        except BackendError as exc: self.error("#documents-result", exc)

    @work(exclusive=False)
    async def index_document(self) -> None:
        item = self.current_document()
        if not item: self.notify("Select a document first.", severity="warning"); return
        if not item.get("index_eligible", False):
            self.notify("This document needs a clearer scan before it can be added to Knowledge.", severity="warning")
            return
        try: await self.client.index(item["document_id"]); self.notify(f"{friendly(item['filename'])} added to Knowledge."); self.refresh_backend()
        except BackendError as exc: self.error("#vision-result" if self.current == "vision" else "#documents-result", exc)

    @work(exclusive=False)
    async def index_all(self) -> None:
        ready = [item for item in self.documents.values() if item.get("index_eligible") and item["document_id"] not in self.indexed_ids]
        if not ready: self.notify("No ready documents need to be added to Knowledge."); return
        self.show_page("documents"); progress = BatchProgress("Adding ready documents to Knowledge", [BatchItem(Path(item["filename"])) for item in ready])
        for document, item in zip(ready, progress.items):
            progress.set_current(item, "processing", "Generating local embeddings"); self.result("#documents-result", progress.render())
            try: await self.client.index(document["document_id"]); progress.set_current(item, "uploaded", "Added to Knowledge")
            except BackendError as exc: progress.set_current(item, "failed", "Could not add document", str(exc))
        progress.current = None; progress.stage = "Knowledge update complete"; self.result("#documents-result", progress.render()); self.refresh_backend()

    @work(exclusive=False)
    async def knowledge_ask(self) -> None:
        question = self.query_one("#knowledge-question", Input).value.strip()
        if not question:
            self.notify("Enter a Knowledge question first.", severity="warning")
            return
        self.result("#knowledge-result", "[b]SEARCHING LOCAL KNOWLEDGE[/b]\n- Retrieving relevant local evidence\n- Preparing a grounded answer from approved local sources")
        try:
            response = await self.client.ask(question)
            response_sources = response.get("sources", [])
            sources = "\n".join(
                f"{index + 1}. {friendly(item.get('filename', 'Local source'))}"
                + (f" - pages {', '.join(str(page) for page in item['page_numbers'])}" if item.get("page_numbers") else "")
                for index, item in enumerate(response_sources)
            ) or "No source records returned."
            self.knowledge_source_pages = {
                str(item["document_id"]): list(item.get("page_numbers", []))
                for item in response_sources if item.get("document_id")
            }
            options = [
                (
                    f"{friendly(item.get('filename', 'Local source'))}"
                    + (f" - pages {', '.join(str(page) for page in item['page_numbers'])}" if item.get("page_numbers") else ""),
                    str(item["document_id"]),
                )
                for item in response_sources if item.get("document_id")
            ]
            self.query_one("#knowledge-source-picker", Select).set_options(options)
            self.result("#knowledge-result", f"[b]ANSWER[/b]\n{response.get('answer', '')}\n\n[b]SOURCES[/b]\n{sources}\n\n[dim]Select a cited source to open it in Documents.[/dim]")
        except BackendError as exc: self.error("#knowledge-result", exc)
    @work(exclusive=False)
    async def knowledge_search(self) -> None:
        try:
            response = await self.client.search(self.query_one("#knowledge-question", Input).value.strip()); chunks = response.get("results", []); body = "\n\n".join(f"[b]{friendly(item.get('filename', 'Local source'))}[/b]\n{item.get('text', '')[:500]}" for item in chunks) or "No matching evidence was found."
            self.result("#knowledge-result", f"[b]MATCHING EVIDENCE[/b]\n{body}")
        except BackendError as exc: self.error("#knowledge-result", exc)

    @work(exclusive=False)
    async def vision_analyze(self) -> None:
        item = self.current_document()
        if not item: self.notify("Choose a document first.", severity="warning"); return
        self.result("#vision-result", "[b]ANALYZING[/b]\n• Checking image quality\n• Running local OCR / vision\n• Evaluating reliability")
        try:
            response = await self.client.vision(item["document_id"]); warnings = "\n".join(f"• {value}" for value in item.get("extraction_warnings", [])) or "None"
            self.result("#vision-result", f"[b]RESULT[/b]\nReliability: {RELIABILITY.get(item.get('reliability_status', ''), 'Analysis complete')}\n\n{response.get('analysis', '')}\n\n[b]WARNINGS[/b]\n{warnings}")
        except BackendError as exc: self.error("#vision-result", exc)
    @work(exclusive=False)
    async def vision_ask(self) -> None:
        item = self.current_document()
        if not item: self.notify("Choose a document first.", severity="warning"); return
        self.result("#vision-result", "[b]ANALYZING IMAGE[/b]\n- Reading the selected local image\n- Running local OCR / vision\n- Preparing a cautious grounded response")
        try:
            response = await self.client.vision(item["document_id"], self.query_one("#vision-question", Input).value.strip())
            warnings = "\n".join(f"- {value}" for value in item.get("extraction_warnings", [])) or "None"
            reliability = RELIABILITY.get(item.get("reliability_status", ""), "Analysis complete")
            self.result("#vision-result", f"[b]IMAGE ANSWER[/b]\nReliability: {reliability}\n\n{response.get('analysis', '')}\n\n[b]WARNINGS[/b]\n{warnings}")
        except BackendError as exc: self.error("#vision-result", exc)
    def vision_text(self) -> None:
        """Start the existing extracted-text worker without awaiting a Worker."""
        self.document_text()
    @work(exclusive=False)
    async def confirm_extraction(self) -> None:
        item = self.current_document(); disagreements = item.get("extraction_disagreements", []) if item else []
        if not item or not disagreements: return
        try:
            await self.client.confirm(item["document_id"], {"field_or_token": disagreements[0]["field_or_token"], "selected_source": str(self.query_one("#confirm-source", Select).value), "manual_value": self.query_one("#confirm-manual", Input).value.strip()}); self.notify("Reading confirmed. The document can now be added to Knowledge."); self.refresh_backend()
        except BackendError as exc: self.error("#vision-result", exc)

    @work(exclusive=True)
    async def run_data_ask_ai(self) -> None:
        picked = self.selected("#dataset-picker")
        if not picked: self.notify("Select a CSV or Excel dataset first.", severity="warning"); return
        question = self.query_one("#data-question", TextArea).text.strip()
        if not question: self.notify("Enter a question about the dataset.", severity="warning"); return
        kind, source_id = picked.split(":", 1) if ":" in picked else ("document", picked)
        structured = self.documents[source_id].get("structured_metadata", {}) if source_id in self.documents else {}
        columns = structured.get("columns", [])
        
        self.result("#data-result", "[b]ANALYZING INTENT[/b]\n• Mapping question to data operation safely...")
        import json
        prompt = f"Map the user's question to a structured DataIntent for this dataset.\nColumns available: {columns}\nAllowed operations: summary, statistics, group_average, filter\nOutput strictly valid JSON with keys: 'operation', 'numeric_column', 'category_column', 'filter_column', 'filter_value'. If ambiguous, add 'explanation_needed' string describing why.\nQuestion: {question}"
        try:
            intent_raw = await self.client.chat(prompt)
            intent = json.loads(intent_raw.get("response", "{}"))
        except Exception as e:
            self.result("#data-result", f"[b]COULD NOT INTERPRET DATA REQUEST[/b]\n\nTry asking a more specific question about {columns}."); return
            
        if "explanation_needed" in intent and intent["explanation_needed"]:
            self.result("#data-result", f"[b]CLARIFICATION NEEDED[/b]\n\n{intent['explanation_needed']}\nFor example: summarize the dataset, compare assets, calculate average."); return
            
        op = intent.get("operation")
        num_col = intent.get("numeric_column")
        cat_col = intent.get("category_column")
        if op not in {"summary", "statistics", "group_average", "filter"}:
            self.result("#data-result", f"[b]COULD NOT INTERPRET DATA REQUEST[/b]\n\nUnsupported operation '{op}' requested."); return
            
        if num_col and num_col not in columns:
            self.result("#data-result", f"[b]COULD NOT INTERPRET DATA REQUEST[/b]\n\nColumn '{num_col}' does not exist in dataset."); return
            
        payload = {"source_kind": kind, "source_id": source_id, "operation": op, "value_column": num_col, "group_by": cat_col, "filter_column": intent.get("filter_column"), "filter_value": intent.get("filter_value")}
        
        self.result("#data-result", "[b]ANALYZING DATA[/b]\n• Running deterministic operation: " + op)
        try:
            response = await self.client.analysis(payload); self.latest_analysis = response; values = response.get("result", {})
            explain_prompt = f"Summarize this deterministic data analysis briefly in one sentence. Do NOT alter any numbers.\nQuestion: {question}\nResult data: {values}"
            explanation = await self.client.chat(explain_prompt)
            
            summary = "\n".join(f"{key}: {value}" for key, value in values.get("averages", {}).items()) if "averages" in values else "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in values.items() if key != "rows")
            
            self.result("#data-result", f"[b]ANALYSIS RESULT[/b]\n\n[#3FB950]Deterministic Result[/]\n{summary or 'Completed.'}\n\n[b]Interpretation[/b]\n{explanation.get('response', '')}\n\n[b]NEXT ACTIONS[/b]\nCreate a chart, export an Excel file, create a report, or send to Agent."); self.refresh_backend()
        except BackendError as exc: self.error("#data-result", exc)

    @work(exclusive=False)
    async def run_analysis(self) -> None:
        picked = self.selected("#dataset-picker")
        if not picked: self.notify("Select a CSV or Excel dataset first.", severity="warning"); return
        kind, source_id = picked.split(":", 1) if ":" in picked else ("document", picked); operation = self.selected("#analysis-operation") or "summary"
        payload = {"source_kind": kind, "source_id": source_id, "operation": operation, "value_column": self.selected("#analysis-value"), "group_by": self.selected("#analysis-group"), "filter_column": self.selected("#analysis-filter-column"), "filter_value": self.query_one("#analysis-filter-value", Input).value.strip() or None}
        self.result("#data-result", "[b]ANALYZING DATA[/b]\n• Reading managed local dataset\n• Calculating deterministic results")
        try:
            response = await self.client.analysis(payload); self.latest_analysis = response; values = response.get("result", {}); averages = values.get("averages", {}); summary = "\n".join(f"{key}: {value}" for key, value in averages.items()) if averages else "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in values.items() if key != "rows")
            self.result("#data-result", f"[b]ANALYSIS COMPLETE[/b]\nRows analyzed: {response.get('row_count')}\n\n{summary or 'The selected operation completed.'}\n\n[b]NEXT ACTIONS[/b]\nCreate a chart, export an Excel file, create a report, or send the finding to Agent."); self.refresh_backend()
        except BackendError as exc: self.error("#data-result", exc)

    def analysis_to_agent(self) -> None:
        if not self.latest_analysis: self.notify("Run an analysis first.", severity="warning"); return
        self.show_page("agent"); self.query_one("#agent-goal", TextArea).text = "Investigate this local data analysis and explain the most important maintenance finding: " + str(self.latest_analysis.get("result", {}))
    def open_deliverable(self, kind: str | None = None) -> None: self.push_screen(DeliverableModal(kind), self.create_deliverable)
    def analysis_table(self) -> tuple[list[list[str | float | int]], list[str]]:
        if not self.latest_analysis: return [["Local workbench", "No analysis selected"]], ["Item", "Result"]
        values = self.latest_analysis.get("result", {}); averages = values.get("averages")
        if isinstance(averages, dict): return [[str(key), float(value)] for key, value in averages.items()], ["Category", "Average"]
        return [[key.replace("_", " ").title(), str(value)] for key, value in values.items() if key != "rows"], ["Measure", "Value"]
    @work(exclusive=False)
    async def create_deliverable(self, form: dict[str, str] | None) -> None:
        if not form: return
        title, kind, description = form["title"], form["kind"], form.get("description", ""); rows, columns = self.analysis_table(); suffix = {"xlsx": ".xlsx", "docx": ".docx", "pptx": ".pptx", "pdf": ".pdf", "chart": ".png"}[kind]; filename = "_".join(title.lower().split())[:80] + suffix
        payload: dict[str, Any] = {"filename": filename, "title": title, "sections": [{"heading": "Summary", "paragraphs": [description or "Local workbench report generated from the current analysis."]}], "sources": []} if kind == "docx" else {"filename": filename, "title": title, "columns": columns, "rows": rows, "sheet_name": "Analysis"}
        self.show_page("artifacts"); self.result("#artifacts-result", "[b]GENERATING VALIDATED FILE[/b]\nCreating locally and validating before it is added to the library.")
        try:
            artifact = await self.client.deliverable(kind, payload)
            dest_path = normalize_path("outputs\\")
            dest_path.mkdir(parents=True, exist_ok=True)
            dest_path = dest_path / artifact['filename']
            await self.client.download(artifact['id'], dest_path)
            self.result("#artifacts-result", f"[b]VALIDATED FILE READY & SAVED[/b]\n✓ {friendly(artifact['filename'])}\nType: {artifact.get('artifact_type', 'file').title()}\nStatus: Validated\n\nAutomatically saved to:\n[#3fb950]{dest_path}[/#3fb950]")
            self.refresh_backend()
        except (BackendError, OSError) as exc: self.error("#artifacts-result", exc)

    @work(exclusive=False)
    async def run_agent(self) -> None:
        goal = self.query_one("#agent-goal", TextArea).text.strip()
        self.result("#agent-result", "[b]WORKING[/b]\n• Understanding request\n• Selecting approved local tools\n• Waiting for safe execution summary")
        try:
            old_artifacts = set(self.artifacts.keys())
            response = await self.client.agent(goal)
            
            new_artifacts_data = await self.client.artifacts()
            saved_paths = []
            for art in new_artifacts_data:
                if art["artifact_id"] not in old_artifacts:
                    dest_path = normalize_path("outputs\\")
                    dest_path.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_path / art['filename']
                    await self.client.download(art['artifact_id'], dest_path)
                    saved_paths.append(str(dest_path))

            
            activity_map = {
                "list_data_sources": "Data sources discovered",
                "data_analysis": "Operational data analyzed",
                "knowledge_search": "Local knowledge searched",
                "create_chart": "Comparison chart created",
                "create_spreadsheet": "Excel analysis created",
                "create_document": "Maintenance recommendation created"
            }
            
            activity_list = []
            for item in response.get("steps", []):
                if item.get("action") == "tool" and item.get("tool"):
                    friendly_tool = activity_map.get(item["tool"], item["tool"].replace("_", " ").title())
                    activity_list.append(f"✓ {friendly_tool}")
            activity_str = "\n".join(activity_list) or "No local tools executed."
            
            sources_list = []
            for item in response.get("sources", []):
                sources_list.append(f"• {item.get('filename', 'Local source')}")
            sources_str = "\n".join(sources_list) or "No sources cited."
            
            result_text = response.get("answer", "Completed with local model.")
            saved_str = ""
            if saved_paths:
                saved_str = "\n\n[b]SAVED ARTIFACTS[/b]\n" + "\n".join(f"[#3fb950]✓ {p}[/#3fb950]" for p in saved_paths)
            
            output = f"[b]TASK[/b]\n{goal}\n\n[b]ACTIVITY[/b]\n{activity_str}\n\n[b]RESULT[/b]\n{result_text}\n\n[b]SOURCES[/b]\n{sources_str}{saved_str}\n\n[b]NEXT ACTIONS[/b]\nReview sources, check Artifacts for deliverables, or continue analysis."
            self.result("#agent-result", output)
            self.refresh_backend()
        except BackendError as exc:
            self.error("#agent-result", exc)
    @work(exclusive=False)
    async def run_sandbox(self) -> None:
        self.result("#sandbox-result", "[b]EXECUTING[/b]\nRunning bounded Python in a backend-managed workspace.")
        try:
            response = await self.client.sandbox(self.query_one("#sandbox-code", TextArea).text); status = response.get("status", "completed"); output = response.get("stdout") or response.get("stderr") or "No output."
            self.result("#sandbox-result", f"[b]{'EXECUTION COMPLETE' if status == 'success' else status.upper()}[/b]\n\n[b]OUTPUT[/b]\n{output}\n\nDuration: {response.get('duration_ms', 0):.0f} ms\nGenerated files: {len(response.get('artifacts', []))}"); self.refresh_backend()
        except BackendError as exc: self.error("#sandbox-result", exc)
    @work(exclusive=False)
    async def save_artifact(self) -> None:
        artifact_id, destination = self.selected("#artifact-picker"), self.query_one("#artifact-save-path", Input).value.strip()
        if not artifact_id or not destination: self.notify("Choose a generated file and save destination.", severity="warning"); return
        try:
            dest_path = normalize_path(destination)
            if dest_path.is_dir() or destination.endswith("/") or destination.endswith("\\") or not dest_path.suffix:
                item = self.artifacts.get(artifact_id, {})
                filename = item.get("filename", f"{artifact_id}.bin")
                dest_path.mkdir(parents=True, exist_ok=True)
                dest_path = dest_path / filename
            await self.client.download(artifact_id, dest_path)
            self.result("#artifacts-result", f"✓ File saved locally to {dest_path}.\n\nThe managed original remains in the Artifacts library.")
        except (BackendError, OSError) as exc: self.error("#artifacts-result", exc)
    def artifact_details(self) -> None:
        artifact_id = self.selected("#artifact-picker")
        if not artifact_id: self.notify("Choose a generated file first.", severity="warning"); return
        item = self.artifacts.get(artifact_id, {}); self.result("#artifacts-result", f"[b]{friendly(item.get('filename', 'Artifact'))}[/b]\nType: {item.get('artifact_type', 'file').title()}\nValidation: ✓ Validated\nSize: {item.get('size_bytes', 0)} bytes\nCreated by: {item.get('source_tool', 'local workbench').replace('_', ' ').title()}")
    @work(exclusive=False)
    async def load_models(self) -> None:
        try:
            models = await self.client.models(); labels = {"general": "Reasoning", "coding": "Coding", "vision": "Vision"}; text = "\n\n".join(f"[b]{labels.get(item.get('id'), item.get('id', '').title())}[/b]\n{item.get('display_name')} • {'✓ Ready' if item.get('available') else '! Unavailable'}\n{item.get('description', '')}" for item in models); self.result("#models-result", text or "No configured models were returned.")
        except BackendError as exc: self.error("#models-result", exc)
    @work(exclusive=False)
    async def load_artifacts(self) -> None: self.refresh_backend()
    @work(exclusive=False)
    async def load_jobs(self) -> None:
        try: self.render_jobs(await self.client.jobs())
        except BackendError as exc: self.error("#jobs-result", exc)
    def start_poll(self) -> None:
        job_id = self.selected("#job-picker")
        if not job_id: self.notify("Choose a task first.", severity="warning"); return
        self.track(job_id, "#jobs-result")
    def track(self, job_id: str | None, target: str) -> None:
        if job_id: self.poll(job_id, target)
    @work(exclusive=False)
    async def poll(self, job_id: str, target: str) -> None:
        async def update(job: dict[str, Any]) -> None:
            self.active_jobs[job_id] = job; progress = job.get("progress"); self.result(target, f"[b]{job_name(job).upper()}[/b]\n{job.get('message', '')}\nStage: {job.get('stage', '').replace('_', ' ')}" + (f"\nProgress: {progress}%" if progress is not None else "\nWorking with local services…"))
            if job.get("status") in {"completed", "failed", "waiting_for_user"}:
                self.active_jobs.pop(job_id, None)
                if job.get("status") == "waiting_for_user": self.notify("A document needs confirmation. Open OCR / Vision.", severity="warning")
                self.refresh_backend()
        try: await poll_job(self.client, job_id, update)
        except BackendError as exc: self.error(target, exc)

if __name__ == "__main__":
    app = SovereignTUI()
    app.run()
