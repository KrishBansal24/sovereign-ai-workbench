"""Textual Pilot regression coverage for the primary terminal workbench."""

import asyncio

from textual.widgets import Button, Input, Select, Static, TextArea

from tui.app import FolderPreviewModal, SovereignTUI, agent_step_label


class _LocalBackendStub:
    """Enough backend state for navigation tests without a network service."""

    async def health(self): return {"backend": "online", "ollama": "available"}
    async def documents(self): return []
    async def artifacts(self): return []
    async def jobs(self): return []
    async def indexed_documents(self): return []
    async def close(self): pass


class _DelayedKnowledgeBackend(_LocalBackendStub):
    """Hold an ask request so Pilot can inspect its honest in-progress state."""

    def __init__(self) -> None:
        self.release = asyncio.Event()

    async def ask(self, question: str):
        assert question == "What guidance applies?"
        await self.release.wait()
        return {"answer": "Inspect the pump before operation.", "sources": [{"document_id": "pump-id", "filename": "pump_manual.pdf", "page_numbers": [12]}]}


def test_agent_trace_uses_friendly_planning_label_for_final_step() -> None:
    assert agent_step_label({"action": "final", "tool": None}) == "Planning"
    assert agent_step_label({"action": "tool", "tool": "knowledge_search"}) == "knowledge_search"


class _FailedSandboxBackend(_LocalBackendStub):
    async def sandbox(self, code: str):
        assert code == "print(10 / 0)"
        return {"status": "failed", "stderr": "ZeroDivisionError: division by zero", "duration_ms": 5, "artifacts": [], "job_id": "sandbox-job"}


class _DelayedVisionBackend(_LocalBackendStub):
    def __init__(self) -> None:
        self.release = asyncio.Event()

    async def vision(self, document_id: str, question: str | None = None):
        assert document_id == "pid-id"
        assert question == "What equipment is visible?"
        await self.release.wait()
        return {"analysis": "P-101 is visible."}


def test_folder_scan_requires_preview_confirmation_before_upload(tmp_path) -> None:
    """A scanned folder is previewed rather than uploaded implicitly."""
    (tmp_path / "procedure.md").write_text("# Procedure", encoding="utf-8")

    async def exercise() -> None:
        app = SovereignTUI()
        app.client = _LocalBackendStub()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("4")
            await pilot.click("#upload-folder")
            app.screen.query_one("#location", Input).value = str(tmp_path)
            app.screen.query_one("#confirm", Button).press()
            await pilot.pause()
            assert isinstance(app.screen, FolderPreviewModal)
            preview = str(app.screen.query_one(".result-panel", Static).renderable)
            assert "procedure.md" in preview
            assert "more file" not in preview
            assert app.folder_progress is None

    asyncio.run(exercise())


def test_knowledge_query_renders_progress_then_grounded_answer() -> None:
    """Long local inference never leaves the Knowledge empty-state on screen."""

    async def exercise() -> None:
        app = SovereignTUI()
        backend = _DelayedKnowledgeBackend()
        app.client = backend
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("5")
            app.query_one("#knowledge-question", Input).value = "What guidance applies?"
            app.query_one("#knowledge-ask", Button).press()
            await pilot.pause()
            assert "SEARCHING LOCAL KNOWLEDGE" in str(app.query_one("#knowledge-result", Static).renderable)
            backend.release.set()
            await pilot.pause()
            rendered = str(app.query_one("#knowledge-result", Static).renderable)
            assert "Inspect the pump before operation." in rendered
            assert "pages 12" in rendered

            app.documents = {"pump-id": {"document_id": "pump-id", "filename": "pump_manual.pdf", "file_type": "pdf", "reliability_status": "accepted", "page_count": 18}}
            app.query_one("#document-picker", Select).set_options((("Pump Manual", "pump-id"),))
            app.query_one("#knowledge-source-picker", Select).value = "pump-id"
            app.query_one("#knowledge-open-source", Button).press()
            await pilot.pause()
            assert app.current == "documents"
            details = str(app.query_one("#documents-result", Static).renderable)
            assert "Pump Manual" in details
            assert "Pages: 12" in details

    asyncio.run(exercise())


def test_sandbox_failure_keeps_captured_runtime_error_visible() -> None:
    """A completed job refresh must not overwrite the operation's useful error."""

    async def exercise() -> None:
        app = SovereignTUI()
        app.client = _FailedSandboxBackend()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("8")
            app.query_one("#sandbox-code", TextArea).text = "print(10 / 0)"
            app.query_one("#run-sandbox", Button).press()
            await pilot.pause()
            await pilot.pause()
            rendered = str(app.query_one("#sandbox-result", Static).renderable)
            assert "ZeroDivisionError" in rendered

    asyncio.run(exercise())


def test_vision_question_renders_progress_before_local_response() -> None:
    """Vision requests never leave the old empty state during local inference."""

    async def exercise() -> None:
        app = SovereignTUI()
        backend = _DelayedVisionBackend()
        app.client = backend
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.documents = {"pid-id": {"document_id": "pid-id", "filename": "nrel_pid_page-2.png", "file_type": "png", "reliability_status": "accepted", "extraction_warnings": ["Small labels require careful review."]}}
            app.selected_document_id = "pid-id"
            await pilot.press("7")
            app.query_one("#vision-question", Input).value = "What equipment is visible?"
            app.query_one("#vision-ask", Button).press()
            await pilot.pause()
            assert "ANALYZING IMAGE" in str(app.query_one("#vision-result", Static).renderable)
            backend.release.set()
            await pilot.pause()
            rendered = str(app.query_one("#vision-result", Static).renderable)
            assert "P-101 is visible." in rendered
            assert "Reliability: Ready" in rendered
            assert "Small labels require careful review." in rendered

    asyncio.run(exercise())


def test_review_only_document_disables_knowledge_action_and_explains_next_step() -> None:
    """Unreliable scans are visibly review-only before a user can index them."""

    async def exercise() -> None:
        app = SovereignTUI()
        app.client = _LocalBackendStub()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.documents = {"doe-id": {"document_id": "doe-id", "filename": "DOE_Engineering_Symbology_PUBLIC.pdf", "file_type": "pdf", "reliability_status": "reupload_required", "index_eligible": False, "page_count": 120, "extraction_warnings": ["Too little readable text was detected."]}}
            app.query_one("#document-picker", Select).set_options((("DOE Engineering Symbology", "doe-id"),))
            app.query_one("#document-picker", Select).value = "doe-id"
            await pilot.pause()
            assert app.query_one("#document-index", Button).disabled
            app.document_details()
            details = str(app.query_one("#documents-result", Static).renderable)
            assert "Needs Clearer Scan" in details
            assert "Re-upload a clearer scan" in details

    asyncio.run(exercise())
