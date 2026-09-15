"""Deterministic local DOCX creation and post-generation validation."""

import re
import tempfile
from copy import copy
from pathlib import Path

from docx import Document
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
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
            document.save(str(output))
            # Validate by reopening and asserting the requested title survived.
            reopened = Document(str(output))
            if not output.exists() or output.stat().st_size == 0 or spec.title not in "\n".join(item.text for item in reopened.paragraphs):
                raise ValueError("Generated DOCX validation failed.")
            return artifact_service.register(output, safe_filename, "document", "docx_generator")

    def create_spreadsheet(self, spec: TableSpec) -> ArtifactMetadata:
        """Generate and reopen a local XLSX workbook from validated tabular data."""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".xlsx")
            workbook = Workbook()
            sheet = workbook.active
            if sheet is None:
                raise ValueError("Active sheet is unexpectedly None")
            sheet.title = self._sheet_name(spec.sheet_name)
            sheet.append(spec.columns)
            for row in spec.rows: sheet.append(row)
            for cell in sheet[1]:
                if cell.font:
                    new_font = copy(cell.font)
                    new_font.bold = True
                    cell.font = new_font
                else:
                    cell.font = Font(bold=True)
            for column_index, column_cells in enumerate(sheet.iter_cols(), start=1):
                if column_cells:
                    column_letter = get_column_letter(column_index)
                    sheet.column_dimensions[column_letter].width = min(40, max(12, max(len(str(cell.value or "")) for cell in column_cells) + 2))
            workbook.save(str(output))
            reopened = load_workbook(str(output), data_only=False)
            reopened_active = reopened.active
            if reopened_active is None:
                raise ValueError("Reopened active sheet is None")
            if reopened.sheetnames != [sheet.title] or list(reopened_active.values)[0] != tuple(spec.columns): raise ValueError("Generated XLSX validation failed.")
            return artifact_service.register(output, output.name, "spreadsheet", "xlsx_generator")

    def create_presentation(self, spec: TableSpec) -> ArtifactMetadata:
        """Generate and reopen a simple local PPTX summary."""
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / self._name(spec.filename, ".pptx")
            presentation = Presentation()
            title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
            if not getattr(title_slide.shapes.title, "has_text_frame", False) or title_slide.shapes.title.text_frame is None:
                raise ValueError("No title frame")
            title_slide.shapes.title.text_frame.text = spec.title
            slide = presentation.slides.add_slide(presentation.slide_layouts[1])
            if not getattr(slide.shapes.title, "has_text_frame", False) or slide.shapes.title.text_frame is None:
                raise ValueError("No slide title frame")
            slide.shapes.title.text_frame.text = "Summary"
            body = slide.placeholders[1]
            if not getattr(body, "has_text_frame", False) or body.text_frame is None:
                raise ValueError("No body frame")
            body.text_frame.text = "\n".join(" • " + " | ".join(map(str,row)) for row in spec.rows[:10])
            presentation.save(str(output))
            reopened = Presentation(str(output))
            if len(reopened.slides) < 2:
                raise ValueError("Generated PPTX validation failed.")
            title_shape = reopened.slides[0].shapes.title
            if not getattr(title_shape, "has_text_frame", False) or title_shape.text_frame is None or title_shape.text_frame.text != spec.title: raise ValueError("Generated PPTX validation failed.")
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
