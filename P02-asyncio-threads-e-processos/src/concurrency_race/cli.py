import asyncio
from pathlib import Path
from typing import Annotated

import typer

from concurrency_race.config import load_scenario
from concurrency_race.reporting import render_table, write_report
from concurrency_race.runner import run_experiment


def race(
    scenario_path: Annotated[
        Path, typer.Option("--scenario", help="Cenário reproduzível em YAML")
    ] = Path("scenario.yaml"),
    output_path: Annotated[
        Path, typer.Option("--output", help="Arquivo JSON com as medições")
    ] = Path("output/results.json"),
) -> None:
    scenario = load_scenario(scenario_path)
    report = asyncio.run(asyncio.wait_for(run_experiment(scenario), scenario.timeout_seconds))
    write_report(report, output_path)
    typer.echo(render_table(report))


def main() -> None:
    typer.run(race)
