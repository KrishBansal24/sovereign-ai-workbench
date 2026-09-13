"""Controlled local artifact storage and metadata registry."""

import json
import re
import shutil
import uuid
import mimetypes
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.artifacts import ArtifactMetadata


class ArtifactNotFoundError(Exception):
    """Raised when an artifact ID does not refer to a managed generated file."""


class ArtifactService:
    """Store generated files beneath project data with UUID-controlled names."""

    def __init__(self) -> None:
        """Create the artifact data directory and metadata registry if needed."""
        self.directory = settings.data_directory / "artifacts"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.directory / "metadata.json"
        if not self.metadata_file.exists():
            self.metadata_file.write_text("{}", encoding="utf-8")

    def register(self, source: Path, filename: str, artifact_type: ArtifactMetadata.__annotations__["artifact_type"], source_tool: str, *, job_id: str | None = None, source_document_ids: list[str] | None = None, provenance: dict[str, str] | None = None) -> ArtifactMetadata:
        """Copy one validated local generated file into controlled artifact storage."""
        if not source.is_file():
            raise ValueError("Generated artifact is unavailable.")
        safe_name = self.safe_filename(filename)
        artifact_id = str(uuid.uuid4())
        destination = self.directory / f"{artifact_id}_{safe_name}"
        # SECURITY: caller never controls destination path; only a basename is retained.
        shutil.copy2(source, destination)
        metadata = ArtifactMetadata(artifact_id=artifact_id, filename=safe_name, media_type=mimetypes.guess_type(safe_name)[0] or "application/octet-stream", artifact_type=artifact_type, size_bytes=destination.stat().st_size, created_at=datetime.now(UTC), validation_status="validated", source_tool=source_tool, job_id=job_id, source_document_ids=source_document_ids or [], provenance=provenance or {})
        records = self._records(); records[artifact_id] = metadata.model_dump(mode="json"); self._save_records(records)
        return metadata

    def list(self) -> list[ArtifactMetadata]:
        """List known artifacts without exposing their filesystem locations."""
        return [ArtifactMetadata.model_validate(value) for value in self._records().values()]

    def path(self, artifact_id: str) -> Path:
        """Resolve a server-issued artifact ID to its controlled stored file."""
        try:
            uuid.UUID(artifact_id)
        except (ValueError, AttributeError) as error:
            raise ArtifactNotFoundError("Artifact not found.") from error
        record = self._records().get(artifact_id)
        if not record:
            raise ArtifactNotFoundError("Artifact not found.")
        matches = list(self.directory.glob(f"{artifact_id}_*"))
        if not matches:
            raise ArtifactNotFoundError("Artifact file is unavailable.")
        return matches[0]

    def _records(self) -> dict[str, dict[str, object]]:
        """Read the lightweight local metadata registry."""
        return json.loads(self.metadata_file.read_text(encoding="utf-8"))

    def _save_records(self, records: dict[str, dict[str, object]]) -> None:
        temporary = self.metadata_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, indent=2), encoding="utf-8")
        temporary.replace(self.metadata_file)

    @staticmethod
    def safe_filename(filename: str) -> str:
        """Return a display basename, rejecting traversal by construction."""
        return re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name).strip("._") or "artifact"


artifact_service = ArtifactService()
