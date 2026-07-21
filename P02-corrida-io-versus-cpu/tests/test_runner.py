import asyncio

from concurrency_race.config import CpuConfig, IoConfig, Scenario
from concurrency_race.reporting import render_table
from concurrency_race.runner import run_experiment


def test_runner_separates_io_and_cpu_and_repeats() -> None:
    scenario = Scenario(
        name="test",
        repetitions=2,
        heartbeat_interval_seconds=0.002,
        io=IoConfig(operations=2, delay_seconds=0.001),
        cpu=CpuConfig(inputs=(10_000, 10_007), process_workers=2),
        timeout_seconds=10,
    )

    report = asyncio.run(run_experiment(scenario))
    table = render_table(report)

    assert len(report.reports) == 6
    assert all(len(item.wall_seconds) == 2 for item in report.reports)
    assert "I/O" in table
    assert "CPU" in table
    assert "asyncio.gather" in table
    assert "processos" in table
