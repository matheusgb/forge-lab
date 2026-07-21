from pathlib import Path

from concurrency_race.config import load_scenario


def test_loads_versioned_scenario() -> None:
    scenario = load_scenario(Path(__file__).parents[1] / "scenario.yaml")

    assert scenario.repetitions == 5
    assert scenario.io.operations == 10
    assert len(scenario.cpu.inputs) == 4
