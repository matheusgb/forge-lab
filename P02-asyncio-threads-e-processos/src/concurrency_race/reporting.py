import json
from pathlib import Path

from tabulate import tabulate

from concurrency_race.runner import ExperimentReport


def _format_seconds(value: float) -> str:
    if value < 0.01:
        return "< 0,01 s"
    return f"{value:.2f} s".replace(".", ",")


def render_table(report: ExperimentReport) -> str:
    rows: list[tuple[str, str, str, str, str]] = []
    baselines: dict[str, float] = {}
    for item in report.reports:
        baseline = baselines.setdefault(item.category, item.median_wall_seconds)
        relative_speed = f"{baseline / item.median_wall_seconds:.2f}x".replace(".", ",")
        rows.append(
            (
                item.category,
                item.strategy,
                _format_seconds(item.median_wall_seconds),
                _format_seconds(item.max_heartbeat_delay_seconds),
                relative_speed,
            )
        )

    return tabulate(
        rows,
        headers=("categoria", "estratégia", "tempo mediano", "maior atraso", "velocidade"),
        tablefmt="github",
    )


def write_report(report: ExperimentReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
