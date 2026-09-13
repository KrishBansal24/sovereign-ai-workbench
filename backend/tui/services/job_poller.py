"""Backend-driven job polling; no fabricated local progress values."""
from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from tui.services.api_client import APIClient, BackendError

TERMINAL_STATES = {"completed", "failed", "waiting_for_user"}

async def poll_job(client: APIClient, job_id: str, callback: Callable[[dict], Awaitable[None]], interval: float = 1.0) -> dict:
    """Poll an opaque backend job until a backend terminal state is reported."""
    while True:
        job = await client.job(job_id)
        await callback(job)
        if job.get("status") in TERMINAL_STATES: return job
        await asyncio.sleep(interval)
