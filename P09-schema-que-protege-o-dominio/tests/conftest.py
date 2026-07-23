from pathlib import Path

import pytest

from schema_guard.scenario import Scenario, load_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scenario() -> Scenario:
    return load_scenario(PROJECT_ROOT / "scenario.yaml")
