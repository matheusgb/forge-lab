from pathlib import Path

import pytest
from pydantic import ValidationError

from query_clinic.config import Scenario, load_scenario

ROOT = Path(__file__).resolve().parents[1]


def test_scenario_closes_complete_distribution_cycles() -> None:
    scenario = load_scenario(ROOT / "scenario.yaml")

    expected_target_rows = scenario.seed.row_count // (
        scenario.seed.tenant_count * scenario.seed.pending_every
    )

    assert expected_target_rows == 120
    assert scenario.target.page_size <= expected_target_rows


def test_scenario_rejects_partial_distribution_cycle() -> None:
    with pytest.raises(ValidationError, match="ciclos completos"):
        Scenario.model_validate(
            {
                "database_url": "postgresql://clinic:clinic@127.0.0.1:55440/query_clinic",
                "seed": {
                    "row_count": 120_001,
                    "customer_count": 400,
                    "tenant_count": 20,
                    "pending_every": 50,
                },
                "target": {
                    "tenant_id": 7,
                    "status": "pending",
                    "page_size": 50,
                    "n_plus_one_rows": 20,
                },
            }
        )


def test_scenario_rejects_unknown_tenant() -> None:
    with pytest.raises(ValidationError, match="precisa existir"):
        Scenario.model_validate(
            {
                "database_url": "postgresql://clinic:clinic@127.0.0.1:55440/query_clinic",
                "seed": {
                    "row_count": 120_000,
                    "customer_count": 400,
                    "tenant_count": 20,
                    "pending_every": 50,
                },
                "target": {
                    "tenant_id": 21,
                    "status": "pending",
                    "page_size": 50,
                    "n_plus_one_rows": 20,
                },
            }
        )


def test_scenario_rejects_database_outside_the_disposable_lab() -> None:
    with pytest.raises(ValidationError, match="clinic@localhost:55440/query_clinic"):
        Scenario.model_validate(
            {
                "database_url": "postgresql://admin:secret@database.example/production",
                "seed": {
                    "row_count": 120_000,
                    "customer_count": 400,
                    "tenant_count": 20,
                    "pending_every": 50,
                },
                "target": {
                    "tenant_id": 7,
                    "status": "pending",
                    "page_size": 50,
                    "n_plus_one_rows": 20,
                },
            }
        )
