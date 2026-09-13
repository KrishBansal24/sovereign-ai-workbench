"""Validated structured specifications for deterministic local deliverables."""

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    """One plain-text section in a locally generated maintenance report."""

    heading: str = Field(min_length=1, max_length=200)
    paragraphs: list[str] = Field(default_factory=list, max_length=30)


class DocumentSpec(BaseModel):
    """Safe DOCX content specification; binary document bytes are never model input."""

    filename: str = Field(default="maintenance_report.docx", max_length=120)
    title: str = Field(min_length=1, max_length=300)
    sections: list[ReportSection] = Field(default_factory=list, max_length=30)
    sources: list[str] = Field(default_factory=list, max_length=30)


class TableSpec(BaseModel):
    """Validated rows/columns used by deterministic spreadsheet/chart/report generators."""

    filename: str = Field(max_length=120)
    title: str = Field(min_length=1, max_length=300)
    columns: list[str] = Field(min_length=1, max_length=50)
    rows: list[list[str | float | int]] = Field(default_factory=list, max_length=5_000)
    sheet_name: str = Field(default="Analysis", min_length=1, max_length=31)


class ChartSpec(TableSpec):
    """Basic local chart specification with validated numeric series."""

    chart_type: str = Field(default="bar", pattern="^(bar|line|scatter|histogram)$")
