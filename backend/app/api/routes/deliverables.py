"""Local structured deliverable-generation endpoints."""

from fastapi import APIRouter, HTTPException

from app.schemas.artifacts import ArtifactMetadata
from app.schemas.deliverables import ChartSpec, DocumentSpec, TableSpec
from app.services.deliverable_service import deliverable_service

router = APIRouter(prefix="/api/deliverables", tags=["deliverables"])


@router.post("/docx", response_model=ArtifactMetadata, summary="Generate and validate a local DOCX report")
def create_docx(spec: DocumentSpec) -> ArtifactMetadata:
    """Generate one validated DOCX from a Pydantic-validated content specification."""
    try:
        return deliverable_service.create_document(spec)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/xlsx", response_model=ArtifactMetadata)
def create_xlsx(spec: TableSpec) -> ArtifactMetadata:
    try: return deliverable_service.create_spreadsheet(spec)
    except (ValueError, OSError) as error: raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/pptx", response_model=ArtifactMetadata)
def create_pptx(spec: TableSpec) -> ArtifactMetadata:
    try: return deliverable_service.create_presentation(spec)
    except (ValueError, OSError) as error: raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/pdf", response_model=ArtifactMetadata)
def create_pdf(spec: TableSpec) -> ArtifactMetadata:
    try: return deliverable_service.create_pdf(spec)
    except (ValueError, OSError) as error: raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/chart", response_model=ArtifactMetadata)
def create_chart(spec: ChartSpec) -> ArtifactMetadata:
    try: return deliverable_service.create_chart(spec)
    except (ValueError, OSError) as error: raise HTTPException(status_code=422, detail=str(error)) from error
