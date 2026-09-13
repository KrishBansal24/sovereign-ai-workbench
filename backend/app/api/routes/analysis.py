"""Local structured-data analysis API."""
from fastapi import APIRouter, HTTPException
from app.schemas.analysis import DataAnalysisRequest, DataAnalysisResult
from app.services.data_analysis_service import data_analysis_service
router = APIRouter(prefix="/api/analysis", tags=["data analysis"])
@router.post("/run", response_model=DataAnalysisResult)
def analyze(request: DataAnalysisRequest) -> DataAnalysisResult:
    try: return data_analysis_service.analyze(request)
    except ValueError as error: raise HTTPException(status_code=422, detail=str(error)) from error
