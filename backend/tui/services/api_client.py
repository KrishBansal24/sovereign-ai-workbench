"""Small async client for the existing local FastAPI API; no business logic."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import httpx


# Local multimodal and reasoning inference can legitimately exceed the short
# request budget appropriate for metadata, jobs, and file listings. This is a
# client wait budget only; backend/model limits remain authoritative.
LOCAL_MODEL_TIMEOUT = httpx.Timeout(330.0)


class BackendError(RuntimeError):
    """Safe backend/API error suitable for display in a terminal UI."""


class APIClient:
    """Local API client with bounded timeouts and safe response extraction."""
    def __init__(self, base_url: str = "http://127.0.0.1:8000", client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(base_url=self.base_url, timeout=httpx.Timeout(30.0))
        self._owned_client = client is None

    async def close(self) -> None:
        if self._owned_client:
            await self._client.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, self._url(path), **kwargs)
        except httpx.RequestError as error:
            raise BackendError("Backend is unavailable. Start FastAPI, then press R to reconnect.") from error
        if response.is_error:
            try: detail = response.json().get("detail", response.text)
            except ValueError: detail = response.text
            raise BackendError(str(detail)[:2000])
        if not response.content: return None
        try: return response.json()
        except ValueError: return response.content

    async def health(self) -> dict[str, Any]: return await self.request("GET", "/api/health")
    async def models(self) -> list[dict[str, Any]]: return await self.request("GET", "/api/models")
    async def documents(self) -> list[dict[str, Any]]:
        """Retrieve every document page, not only what fits in a selector viewport."""
        documents: list[dict[str, Any]] = []; offset = 0; page_size = 50
        while True:
            response = await self.request("GET", f"/api/documents?limit={page_size}&offset={offset}")
            page = response["documents"]
            documents.extend(page)
            if not response.get("has_more", False): return documents
            next_offset = response.get("offset", offset) + len(page)
            if not page or next_offset <= offset: raise BackendError("Document listing pagination did not advance.")
            offset = next_offset
    async def indexed_documents(self) -> list[dict[str, Any]]: return (await self.request("GET", "/api/knowledge/documents"))["documents"]
    async def artifacts(self) -> list[dict[str, Any]]: return await self.request("GET", "/api/artifacts")
    async def clear_artifacts(self) -> None: await self.request("DELETE", "/api/artifacts")
    async def job(self, job_id: str) -> dict[str, Any]: return await self.request("GET", f"/api/jobs/{job_id}")
    async def jobs(self) -> list[dict[str, Any]]: return await self.request("GET", "/api/jobs")
    async def upload(self, path: Path, background: bool = True) -> dict[str, Any]:
        if not path.is_file(): raise BackendError("The selected upload path is not a file.")
        with path.open("rb") as handle:
            return await self.request("POST", "/api/documents/upload-job" if background else "/api/documents/upload", files={"file": (path.name, handle)})
    async def document_text(self, document_id: str) -> dict[str, Any]: return await self.request("GET", f"/api/documents/{document_id}/text")
    async def agent(self, goal: str) -> dict[str, Any]: return await self.request("POST", "/api/agent/run", json={"goal": goal}, timeout=LOCAL_MODEL_TIMEOUT)
    async def search(self, query: str) -> dict[str, Any]: return await self.request("POST", "/api/knowledge/search", json={"query": query})
    async def ask(self, question: str) -> dict[str, Any]: return await self.request("POST", "/api/knowledge/ask", json={"question": question}, timeout=LOCAL_MODEL_TIMEOUT)
    async def index(self, document_id: str) -> dict[str, Any]: return await self.request("POST", f"/api/knowledge/documents/{document_id}/index")
    async def vision(self, document_id: str, question: str | None = None) -> dict[str, Any]:
        return await self.request("POST", f"/api/vision/{document_id}/{'ask' if question else 'analyze'}", json={"question": question} if question else None, timeout=LOCAL_MODEL_TIMEOUT)
    async def confirm(self, document_id: str, payload: dict[str, str]) -> dict[str, Any]: return await self.request("POST", f"/api/documents/{document_id}/confirm-extraction", json=payload)
    async def sandbox(self, code: str) -> dict[str, Any]: return await self.request("POST", "/api/sandbox/execute", json={"code": code})
    async def analysis(self, payload: dict[str, Any]) -> dict[str, Any]: return await self.request("POST", "/api/analysis/run", json=payload)
    async def chat(self, message: str) -> dict[str, Any]: return await self.request("POST", "/api/chat", json={"message": message}, timeout=LOCAL_MODEL_TIMEOUT)
    async def deliverable(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]: return await self.request("POST", f"/api/deliverables/{kind}", json=payload)
    async def download(self, artifact_id: str, destination: Path) -> Path:
        content = await self.request("GET", f"/api/artifacts/{artifact_id}/download")
        destination.write_bytes(content)
        return destination
    def _url(self, path: str) -> str:
        return path if path.startswith("http") else f"{self.base_url}{path}"
