import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter

Workload = Callable[[], Awaitable[tuple[int, ...]]]


@dataclass(frozen=True)
class Measurement:
    wall_seconds: float
    max_heartbeat_delay_seconds: float
    result: tuple[int, ...]


async def _heartbeat(
    stop: asyncio.Event,
    interval_seconds: float,
    delays: list[float],
) -> None:
    loop = asyncio.get_running_loop()
    previous = loop.time()
    while not stop.is_set():
        await asyncio.sleep(interval_seconds)
        current = loop.time()
        delays.append(max(0.0, current - previous - interval_seconds))
        previous = current


async def measure(workload: Workload, heartbeat_interval_seconds: float) -> Measurement:
    stop = asyncio.Event()
    heartbeat_delays: list[float] = []
    heartbeat_task = asyncio.create_task(
        _heartbeat(stop, heartbeat_interval_seconds, heartbeat_delays)
    )
    await asyncio.sleep(0)

    started_at = perf_counter()
    result = await workload()
    wall_seconds = perf_counter() - started_at

    stop.set()
    await heartbeat_task
    return Measurement(
        wall_seconds=wall_seconds,
        max_heartbeat_delay_seconds=max(heartbeat_delays, default=0.0),
        result=result,
    )
