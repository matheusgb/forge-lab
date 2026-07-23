import asyncio
from pathlib import Path

from broker_models.comparison import render_report
from broker_models.experiment import run_experiment


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    result = asyncio.run(run_experiment(project))
    print(render_report(result))


if __name__ == "__main__":
    main()
