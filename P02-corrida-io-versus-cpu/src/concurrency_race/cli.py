import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from concurrency_race.config import load_scenario
from concurrency_race.reporting import render_table, write_report
from concurrency_race.runner import run_experiment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compara estratégias para I/O e CPU")
    parser.add_argument("--scenario", type=Path, default=Path("scenario.yaml"))
    parser.add_argument("--output", type=Path, default=Path("output/results.json"))
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    scenario = load_scenario(args.scenario)
    report = asyncio.run(asyncio.wait_for(run_experiment(scenario), scenario.timeout_seconds))
    write_report(report, args.output)
    print(render_table(report))
