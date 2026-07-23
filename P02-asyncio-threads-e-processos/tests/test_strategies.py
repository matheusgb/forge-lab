from concurrency_race.measurement import measure
from concurrency_race.strategies import (
    cpu_direct,
    cpu_processes,
    cpu_threads,
    io_blocking_loop,
    io_concurrent,
    io_sequential,
)


async def test_io_strategies_return_same_results() -> None:
    inputs = (1, 2, 3)
    sequential = await io_sequential(inputs, 0.001)
    concurrent = await io_concurrent(inputs, 0.001)
    blocking = await io_blocking_loop(inputs, 0.001)
    assert sequential == concurrent == blocking == (2, 4, 6)


async def test_blocking_call_delays_event_loop_heartbeat() -> None:
    inputs = (1, 2, 3)
    concurrent = await measure(lambda: io_concurrent(inputs, 0.02), 0.002)
    blocking = await measure(lambda: io_blocking_loop(inputs, 0.02), 0.002)
    assert blocking.max_heartbeat_delay_seconds > 0.04
    assert blocking.max_heartbeat_delay_seconds > concurrent.max_heartbeat_delay_seconds + 0.03


async def test_cpu_strategies_return_same_results() -> None:
    inputs = (10_000, 10_013)
    direct = await cpu_direct(inputs)
    threads = await cpu_threads(inputs)
    processes = await cpu_processes(inputs, workers=2)
    assert direct == threads == processes
