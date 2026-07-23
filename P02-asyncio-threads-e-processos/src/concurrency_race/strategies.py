import asyncio
import time
from concurrent.futures import ProcessPoolExecutor


async def simulated_io(value: int, delay_seconds: float) -> int:
    await asyncio.sleep(delay_seconds)
    return value * 2


async def io_sequential(inputs: tuple[int, ...], delay_seconds: float) -> tuple[int, ...]:
    results: list[int] = []
    for value in inputs:
        results.append(await simulated_io(value, delay_seconds))
    return tuple(results)


async def io_concurrent(inputs: tuple[int, ...], delay_seconds: float) -> tuple[int, ...]:
    results = await asyncio.gather(*(simulated_io(value, delay_seconds) for value in inputs))
    return tuple(results)


async def io_blocking_loop(inputs: tuple[int, ...], delay_seconds: float) -> tuple[int, ...]:
    results: list[int] = []
    for value in inputs:
        time.sleep(delay_seconds)
        results.append(value * 2)
    return tuple(results)


def cpu_work(iterations: int) -> int:
    total = 0
    for value in range(iterations):
        total = (total + value * value) % 1_000_000_007
    return total


async def cpu_direct(inputs: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(cpu_work(value) for value in inputs)


async def cpu_threads(inputs: tuple[int, ...]) -> tuple[int, ...]:
    results = await asyncio.gather(*(asyncio.to_thread(cpu_work, value) for value in inputs))
    return tuple(results)


async def cpu_processes(inputs: tuple[int, ...], workers: int) -> tuple[int, ...]:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = tuple(loop.run_in_executor(executor, cpu_work, value) for value in inputs)
        results = await asyncio.gather(*futures)
    return tuple(results)
