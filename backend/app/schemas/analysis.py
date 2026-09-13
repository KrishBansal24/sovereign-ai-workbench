"""Safe local structured-data analysis contracts."""
from typing import Literal
from pydantic import BaseModel, Field

class DataAnalysisRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=64)
    source_kind: Literal["document", "artifact"] = "document"
    operation: Literal["summary", "group_average", "filter", "statistics"] = "summary"
    value_column: str | None = Field(default=None, max_length=200)
    group_by: str | None = Field(default=None, max_length=200)
    filter_column: str | None = Field(default=None, max_length=200)
    filter_value: str | None = Field(default=None, max_length=500)

class DataAnalysisResult(BaseModel):
    source_id: str
    operation: str
    row_count: int
    columns: list[str]
    result: dict[str, object]
    job_id: str | None = None
