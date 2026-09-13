"""Deterministic local DOCX creation and post-generation validation."""

import re
import tempfile
from pathlib import Path

from docx import Document
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from reportlab.pdfgen import canvas
from pypdf import PdfReader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.schemas.artifacts import ArtifactMetadata
from app.schemas.deliverables import ChartSpec, DocumentSpec, TableSpec
from app.services.artifact_service import artifact_service


class DeliverableService:
    """Generate professional but deliberately simple local DOCX reports."""

    def create_document(self, spec: DocumentSpec) -> ArtifactMetadata:
        """Create, reopen, validate, and register a DOCX from structured content."""
        safe_filename = re.sub(r"[^A-Za-z0-9._-]", "_", Path(spec.filename).name)
        if not safe_filename.lower().endswith(".docx"):
            safe_filename += ".docx"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / safe_filename
            document = Document()
            document.add_heading(spec.title, level=0)
            for section in spec.sections:
                document.add_heading(section.heading, level=1)
                for paragraph in section.paragraphs:
                    document.add_paragraph(paragraph)
            if spec.sources:
                document.add_heading("Sources", level=1)
                for source in spec.sources:
                    document.add_paragraph(source, style="List Bullet")
            document.save(output)
            # Validate by reopening and asserting the requested title survived.
            reopened = Document(output)
            if not output.exists() or output.stat().st_size == 0 or spec.title not in "\n".join(item.text for item in reopened.paragraphs):
                raise ValueError("Generated DOCX validation failed.")
            return artifact_service.register(output, safe_filename, "document", "docx_generator")

    def create_spreadsheet(self, spec: TableSpec) -> ArtifactMetadata:
        """Generate and reopen a local XLSX workbook from validated tabular data."""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".xlsx")
            workbook = Workbook(); sheet = workbook.active; sheet.title = self._sheet_name(spec.sheet_name); sheet.append(spec.columns)
            for row in spec.rows: sheet.append(row)
            for cell in sheet[1]: cell.font = cell.font.copy(bold=True)
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = min(40, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
            workbook.save(output)
            reopened = load_workbook(output, data_only=False)
            if reopened.sheetnames != [sheet.title] or list(reopened.active.values)[0] != tuple(spec.columns): raise ValueError("Generated XLSX validation failed.")
            return artifact_service.register(output, output.name, "spreadsheet", "xlsx_generator")

    def create_presentation(self, spec: TableSpec) -> ArtifactMetadata:
        """Generate and reopen a simple local PPTX summary."""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".pptx")
            presentation = Presentation(); title_slide = presentation.slides.add_slide(presentation.slide_layouts[0]); title_slide.shapes.title.text = spec.title
            slide = presentation.slides.add_slide(presentation.slide_layouts[1]); slide.shapes.title.text = "Summary"; slide.placeholders[1].text = "\n".join(" • " + " | ".join(map(str,row)) for row in spec.rows[:10]); presentation.save(output)
            reopened = Presentation(output)
            if len(reopened.slides) < 2 or reopened.slides[0].shapes.title.text != spec.title: raise ValueError("Generated PPTX validation failed.")
            return artifact_service.register(output, output.name, "presentation", "pptx_generator")

    def create_pdf(self, spec: TableSpec) -> ArtifactMetadata:
        """Generate and validate a one-page local PDF summary."""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".pdf"); pdf = canvas.Canvas(str(output)); pdf.drawString(72, 760, spec.title)
            for index,row in enumerate(spec.rows[:30]): pdf.drawString(72, 730-index*18, " | ".join(map(str,row)))
            pdf.save()
            if not output.read_bytes().startswith(b"%PDF-") or len(PdfReader(output).pages) < 1: raise ValueError("Generated PDF validation failed.")
            return artifact_service.register(output, output.name, "pdf", "pdf_generator")

    def create_chart(self, spec: ChartSpec) -> ArtifactMetadata:
        """Generate and validate a local PNG chart using the first two columns."""
        if len(spec.columns) < 2: raise ValueError("Chart requires at least two columns.")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".png"); labels=[str(row[0]) for row in spec.rows]; values=[float(row[1]) for row in spec.rows]
            figure, axis = plt.subplots()
            if spec.chart_type == "bar": axis.bar(labels, values)
            elif spec.chart_type == "line": axis.plot(labels, values)
            elif spec.chart_type == "scatter": axis.scatter(labels, values)
            else: axis.hist(values)
            axis.set_title(spec.title); figure.savefig(output); plt.close(figure)
            from PIL import Image
            with Image.open(output) as image:
                if image.width < 10 or image.height < 10: raise ValueError("Generated chart validation failed.")
            return artifact_service.register(output, output.name, "chart", "chart_generator")

    @staticmethod
    def _name(filename: str, suffix: str) -> str:
        """Sanitize an LLM/user-provided display filename into a controlled basename."""
        name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name).strip("._") or "artifact"
        return name if name.lower().endswith(suffix) else name + suffix

    @staticmethod
    def _sheet_name(value: str) -> str:
        return re.sub(r"[\\/:*?\[\]]", "_", value)[:31] or "Analysis"


deliverable_service = DeliverableService()
