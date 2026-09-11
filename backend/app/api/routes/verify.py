"""Temporary local developer verification interface routes."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(tags=["developer verification"])
STATIC_DIRECTORY = Path(__file__).resolve().parents[2] / "static"


@router.get("/verify", include_in_schema=False)
def verification_page() -> FileResponse:
    """Serve the intentionally temporary local testing client."""
    return FileResponse(STATIC_DIRECTORY / "verify.html")


@router.get("/verify/static/{asset_name}", include_in_schema=False)
def verification_asset(asset_name: str) -> FileResponse:
    """Serve only the two fixed developer-page assets, never arbitrary paths."""
    # SECURITY: explicit allow-list prevents traversal and filesystem browsing.
    if asset_name not in {"verify.css", "verify.js"}:
        return FileResponse(STATIC_DIRECTORY / "verify.html", status_code=404)
    return FileResponse(STATIC_DIRECTORY / asset_name)
