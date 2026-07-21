import json
from pathlib import Path

from concurrency_race.runner import ExperimentReport


def render_table(report: ExperimentReport) -> str:
    rows = [
        "categoria | estratégia            | mediana     | maior atraso",
        "----------|-----------------------|-------------|-------------",
    ]
    for item in report.reports:
        rows.append(
            f"{item.category:<9} | {item.strategy:<21} | "
            f"{item.median_wall_seconds:>9.4f}s | "
            f"{item.max_heartbeat_delay_seconds:>10.4f}s"
        )
    return "\n".join(rows)


def write_report(report: ExperimentReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
