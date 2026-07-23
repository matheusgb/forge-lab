import asyncio
from time import perf_counter

from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient


async def measure(app: FastAPI, path: str, requests: int, delay: float) -> float:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        started = perf_counter()
        responses = await asyncio.gather(
            *(client.get(path, params={"delay_seconds": delay}) for _ in range(requests))
        )
        elapsed = perf_counter() - started

    assert all(response.status_code == 200 for response in responses)
    return elapsed


def test_def_protects_event_loop_from_blocking_library(app: FastAPI) -> None:
    sync_elapsed = asyncio.run(measure(app, "/work/sync", requests=3, delay=0.05))
    async_elapsed = asyncio.run(measure(app, "/work/async-blocking", requests=3, delay=0.05))

    assert async_elapsed > sync_elapsed * 1.8
