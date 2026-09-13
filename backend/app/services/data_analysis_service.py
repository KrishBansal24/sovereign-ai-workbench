"""Deterministic CSV/XLSX analysis over application-owned input files."""
from pathlib import Path
import pandas as pd
from app.schemas.analysis import DataAnalysisRequest, DataAnalysisResult
from app.services.artifact_service import artifact_service
from app.services.documents.document_service import document_service
from app.services.jobs import job_progress_service

class DataAnalysisService:
    def analyze(self, request: DataAnalysisRequest) -> DataAnalysisResult:
        path, source_name = self._source(request.source_kind, request.source_id)
        job = job_progress_service.create(
            "data_analysis", "validating_input", "Validating managed structured-data input.",
            display_name=f"Analyze — {source_name}", resource_name=source_name, resource_type="dataset",
        )
        try:
            job_progress_service.update(job.job_id, "running", "reading_data", "Reading CSV or XLSX locally.", 30)
            frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_excel(path)
            if frame.empty: raise ValueError("Structured data is empty.")
            job_progress_service.update(job.job_id, "running", "analyzing_data", "Calculating deterministic results.", 65)
            result = self._operation(frame, request)
            job_progress_service.update(job.job_id, "completed", "completed", "Data analysis completed.", 100)
            return DataAnalysisResult(source_id=request.source_id, operation=request.operation, row_count=len(frame), columns=[str(x) for x in frame.columns], result=result, job_id=job.job_id)
        except (ValueError, OSError, pd.errors.ParserError) as error:
            job_progress_service.update(job.job_id, "failed", "failed", "Data analysis could not be completed.", 100)
            raise ValueError(str(error)) from error
    @staticmethod
    def _source(kind: str, source_id: str) -> tuple[Path, str]:
        """Resolve a controlled file while retaining its safe display name."""
        if kind == "artifact":
            path = artifact_service.path(source_id)
            source_name = next((item.filename for item in artifact_service.list() if item.artifact_id == source_id), "Generated dataset")
        else:
            metadata = document_service.get_metadata(source_id)
            if metadata.file_type not in {"csv", "xlsx"}: raise ValueError("Only CSV or XLSX managed inputs are supported.")
            path = document_service.files_directory / f"{source_id}.{metadata.file_type.value}"
            source_name = metadata.filename
        if path.suffix.lower() not in {".csv", ".xlsx"}: raise ValueError("Only CSV or XLSX managed inputs are supported.")
        return path, source_name
    @staticmethod
    def _operation(frame: pd.DataFrame, request: DataAnalysisRequest) -> dict[str, object]:
        if request.filter_column:
            if request.filter_column not in frame.columns: raise ValueError("Filter column is not present.")
            frame = frame[frame[request.filter_column].astype(str) == (request.filter_value or "")]
        if request.operation == "filter": return {"rows": frame.fillna("").to_dict(orient="records")}
        if request.value_column is None or request.value_column not in frame.columns: raise ValueError("A valid numeric value_column is required.")
        values = pd.to_numeric(frame[request.value_column], errors="coerce").dropna()
        if values.empty: raise ValueError("The selected column contains no numeric values.")
        if request.operation == "group_average":
            if not request.group_by or request.group_by not in frame.columns: raise ValueError("A valid group_by column is required.")
            grouped = frame.assign(_value=pd.to_numeric(frame[request.value_column], errors="coerce")).dropna(subset=["_value"]).groupby(request.group_by)["_value"].mean()
            return {"averages": {str(k): float(v) for k,v in grouped.items()}}
        return {"count": int(values.count()), "average": float(values.mean()), "min": float(values.min()), "max": float(values.max()), "standard_deviation": float(values.std(ddof=0))}

data_analysis_service = DataAnalysisService()
