import platform
import statistics
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass

from concurrency_race.config import Scenario
from concurrency_race.measurement import Measurement, measure
from concurrency_race.strategies import (
    cpu_direct,
    cpu_processes,
    cpu_threads,
    io_blocking_loop,
    io_concurrent,
    io_sequential,
)


@dataclass(frozen=True)
class StrategyReport:
    category: str
    strategy: str
    wall_seconds: tuple[float, ...]
    median_wall_seconds: float
    max_heartbeat_delay_seconds: float
    result: tuple[int, ...]


@dataclass(frozen=True)
class ExperimentReport:
    scenario: str
    python: str
    platform: str
    repetitions: int
    reports: tuple[StrategyReport, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


WorkloadFactory = Callable[[], Awaitable[tuple[int, ...]]]


async def _repeat(
    category: str,
    strategy: str,
    workload: WorkloadFactory,
    repetitions: int,
    heartbeat_interval_seconds: float,
) -> StrategyReport:
    measurements: list[Measurement] = []
    for _ in range(repetitions):
        measurements.append(await measure(workload, heartbeat_interval_seconds))

    expected = measurements[0].result
    if any(item.result != expected for item in measurements):
        raise AssertionError(f"{strategy} returned inconsistent results")

    wall_seconds = tuple(item.wall_seconds for item in measurements)
    return StrategyReport(
        category=category,
        strategy=strategy,
        wall_seconds=wall_seconds,
        median_wall_seconds=statistics.median(wall_seconds),
        max_heartbeat_delay_seconds=max(item.max_heartbeat_delay_seconds for item in measurements),
        result=expected,
    )


def _assert_same_results(reports: tuple[StrategyReport, ...], category: str) -> None:
    category_results = {report.result for report in reports if report.category == category}
    if len(category_results) != 1:
        raise AssertionError(f"{category} strategies returned different results")


async def run_experiment(scenario: Scenario) -> ExperimentReport:
    io_inputs = tuple(range(scenario.io.operations))
    cpu_inputs = scenario.cpu.inputs
    repetitions = scenario.repetitions
    heartbeat = scenario.heartbeat_interval_seconds

    reports = (
        await _repeat(
            "I/O",
            "espera sequencial",
            lambda: io_sequential(io_inputs, scenario.io.delay_seconds),
            repetitions,
            heartbeat,
        ),
        await _repeat(
            "I/O",
            "asyncio.gather",
            lambda: io_concurrent(io_inputs, scenario.io.delay_seconds),
            repetitions,
            heartbeat,
        ),
        await _repeat(
            "I/O",
            "time.sleep bloqueante",
            lambda: io_blocking_loop(io_inputs, scenario.io.delay_seconds),
            repetitions,
            heartbeat,
        ),
        await _repeat(
            "CPU",
            "execução direta",
            lambda: cpu_direct(cpu_inputs),
            repetitions,
            heartbeat,
        ),
        await _repeat(
            "CPU",
            "asyncio.to_thread",
            lambda: cpu_threads(cpu_inputs),
            repetitions,
            heartbeat,
        ),
        await _repeat(
            "CPU",
            "processos",
            lambda: cpu_processes(cpu_inputs, scenario.cpu.process_workers),
            repetitions,
            heartbeat,
        ),
    )
    _assert_same_results(reports, "I/O")
    _assert_same_results(reports, "CPU")
    return ExperimentReport(
        scenario=scenario.name,
        python=platform.python_version(),
        platform=platform.platform(),
        repetitions=repetitions,
        reports=reports,
    )
