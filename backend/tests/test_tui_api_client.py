"""Client-layer tests for the separate terminal UI; no Ollama required."""
import httpx
import asyncio
from tui.services.api_client import APIClient, BackendError
from tui.services.job_poller import TERMINAL_STATES


def test_client_returns_json_and_uses_local_api_path() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/health"
        return httpx.Response(200, json={"backend": "online"})
    async def run() -> None:
        client = APIClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        assert await client.health() == {"backend": "online"}
    asyncio.run(run())


def test_client_converts_safe_backend_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response: return httpx.Response(422, json={"detail": "Invalid request"})
    async def run() -> None:
        client = APIClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        try:
            await client.sandbox("")
            assert False, "Expected controlled backend error"
        except BackendError as error:
            assert "Invalid request" in str(error)
    asyncio.run(run())


def test_waiting_for_user_is_a_terminal_poll_state() -> None:
    assert {"completed", "failed", "waiting_for_user"} <= TERMINAL_STATES


def test_document_client_follows_all_pages() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        page = [{"document_id": str(number), "filename": f"document-{number}.txt"} for number in range(offset, min(offset + 3, 10))]
        return httpx.Response(200, json={"documents": page, "offset": offset, "limit": 3, "total": 10, "has_more": offset + 3 < 10})
    async def run() -> None:
        client = APIClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        documents = await client.documents()
        assert len(documents) == 10 and documents[-1]["filename"] == "document-9.txt"
    asyncio.run(run())


def test_document_text_uses_controlled_document_route() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/documents/safe-id/text"
        return httpx.Response(200, json={"document_id": "safe-id", "text": "Extracted local text"})
    async def run() -> None:
        client = APIClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        assert (await client.document_text("safe-id"))["text"] == "Extracted local text"
    asyncio.run(run())


def test_local_model_calls_have_a_longer_client_wait_budget() -> None:
    """Slow local inference is not misreported as an offline backend."""
    observed: list[float | None] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request.extensions["timeout"]["read"])
        return httpx.Response(200, json={"analysis": "local"} if "/vision/" in request.url.path else {"answer": "local"})

    async def run() -> None:
        client = APIClient(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        await client.ask("question")
        await client.vision("document", "question")
        await client.agent("goal")

    asyncio.run(run())
    assert observed == [330.0, 330.0, 330.0]
