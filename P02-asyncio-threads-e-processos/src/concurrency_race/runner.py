import platform
import statistics
from dataclasses import asdict, dataclass
from functools import partial

from concurrency_race.config import Scenario
from concurrency_race.measurement import Workload, measure
from concurrency_race.strategies import (
    cpu_direct,
    cpu_processes,
    cpu_threads,
    io_blocking_loop,
    io_concurrent,
    io_sequential,
)


@dataclass(frozen=True)
class Strategy:
    category: str
    name: str
    workload: Workload


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


async def _repeat(
    strategy: Strategy,
    repetitions: int,
    heartbeat_interval_seconds: float,
) -> StrategyReport:
    measurements = [
        await measure(strategy.workload, heartbeat_interval_seconds) for _ in range(repetitions)
    ]
    expected = measurements[0].result
    if any(item.result != expected for item in measurements):
        raise AssertionError(f"{strategy.name} returned inconsistent results")

    wall_seconds = tuple(item.wall_seconds for item in measurements)
    return StrategyReport(
        category=strategy.category,
        strategy=strategy.name,
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
    cpu_inputs = tuple(scenario.cpu.inputs)
    strategies = (
        Strategy(
            "I/O",
            "espera sequencial",
            partial(io_sequential, io_inputs, scenario.io.delay_seconds),
        ),
        Strategy(
            "I/O",
            "asyncio.gather",
            partial(io_concurrent, io_inputs, scenario.io.delay_seconds),
        ),
        Strategy(
            "I/O",
            "time.sleep bloqueante",
            partial(io_blocking_loop, io_inputs, scenario.io.delay_seconds),
        ),
        Strategy("CPU", "execução direta", partial(cpu_direct, cpu_inputs)),
        Strategy("CPU", "asyncio.to_thread", partial(cpu_threads, cpu_inputs)),
        Strategy(
            "CPU",
            "processos",
            partial(cpu_processes, cpu_inputs, scenario.cpu.process_workers),
        ),
    )
    reports = tuple(
        [
            await _repeat(
                strategy,
                scenario.repetitions,
                scenario.heartbeat_interval_seconds,
            )
            for strategy in strategies
        ]
    )
    _assert_same_results(reports, "I/O")
    _assert_same_results(reports, "CPU")
    return ExperimentReport(
        scenario=scenario.name,
        python=platform.python_version(),
        platform=platform.platform(),
        repetitions=scenario.repetitions,
        reports=reports,
    )
