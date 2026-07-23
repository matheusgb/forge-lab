from pathlib import Path
from typing import cast

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Table, UniqueConstraint

from schema_guard.models import Order
from schema_guard.scenario import load_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_model_declares_database_invariants() -> None:
    table = cast(Table, Order.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}

    assert table.c.tenant_id.nullable is False
    assert table.c.external_id.nullable is False
    assert table.c.total_cents.nullable is False
    assert any(isinstance(item, ForeignKeyConstraint) for item in table.constraints)
    assert sum(isinstance(item, CheckConstraint) for item in table.constraints) == 2
    assert any(isinstance(item, UniqueConstraint) for item in table.constraints)
    assert "fk_orders_tenant_id_tenants" in constraint_names
    assert "ck_orders_total_cents_positive" in constraint_names
    assert "uq_orders_tenant_external_id" in constraint_names


def test_scenario_is_validated() -> None:
    scenario = load_scenario(PROJECT_ROOT / "scenario.yaml")

    assert scenario.tenant_a_id != scenario.tenant_b_id
    assert scenario.valid_total_cents > 0
