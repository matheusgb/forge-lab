import json
from pathlib import Path

from concurrency_race.runner import ExperimentReport


def _format_seconds(value: float) -> str:
    if value < 0.01:
        return "< 0,01 s"
    return f"{value:.2f} s".replace(".", ",")


def render_table(report: ExperimentReport) -> str:
    rows = [
        "categoria | estratégia            | tempo mediano | maior atraso | velocidade",
        "----------|-----------------------|---------------|--------------|-----------",
    ]
    baselines: dict[str, float] = {}
    for item in report.reports:
        baseline = baselines.setdefault(item.category, item.median_wall_seconds)
        relative_speed = baseline / item.median_wall_seconds
        relative_speed_text = f"{relative_speed:.2f}x".replace(".", ",")
        rows.append(
            f"{item.category:<9} | {item.strategy:<21} | "
            f"{_format_seconds(item.median_wall_seconds):>13} | "
            f"{_format_seconds(item.max_heartbeat_delay_seconds):>12} | "
            f"{relative_speed_text:>9}"
        )
    return "\n".join(rows)


def write_report(report: ExperimentReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
