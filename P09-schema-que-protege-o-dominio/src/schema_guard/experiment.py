from dataclasses import dataclass

from sqlalchemy import Engine, delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.base import Executable

from schema_guard.models import Order, Tenant
from schema_guard.scenario import Scenario


@dataclass(frozen=True)
class Violation:
    case: str
    database_error: str


@dataclass(frozen=True)
class ExperimentResult:
    violations: tuple[Violation, ...]
    same_external_id_across_tenants: int


def _expect_rejection(engine: Engine, case: str, statement: Executable) -> Violation:
    try:
        with engine.begin() as connection:
            connection.execute(statement)
    except IntegrityError as error:
        return Violation(case=case, database_error=type(error.orig).__name__)
    raise AssertionError(f"O PostgreSQL aceitou o caso invalido: {case}")


def run_constraint_probes(engine: Engine, scenario: Scenario) -> ExperimentResult:
    with engine.begin() as connection:
        connection.execute(delete(Order))
        connection.execute(delete(Tenant))
        connection.execute(
            insert(Tenant),
            [
                {"id": scenario.tenant_a_id, "name": "Tenant A"},
                {"id": scenario.tenant_b_id, "name": "Tenant B"},
            ],
        )
        connection.execute(
            insert(Order).values(
                tenant_id=scenario.tenant_a_id,
                external_id=scenario.external_id,
                total_cents=scenario.valid_total_cents,
                status=scenario.valid_status,
            )
        )

    violations = (
        _expect_rejection(
            engine,
            "FK órfã",
            insert(Order).values(
                tenant_id=scenario.orphan_tenant_id,
                external_id="orphan",
                total_cents=scenario.valid_total_cents,
                status=scenario.valid_status,
            ),
        ),
        _expect_rejection(
            engine,
            "NOT NULL",
            insert(Order).values(
                tenant_id=scenario.tenant_a_id,
                external_id=None,
                total_cents=scenario.valid_total_cents,
                status=scenario.valid_status,
            ),
        ),
        _expect_rejection(
            engine,
            "CHECK",
            insert(Order).values(
                tenant_id=scenario.tenant_a_id,
                external_id="free-order",
                total_cents=0,
                status=scenario.valid_status,
            ),
        ),
        _expect_rejection(
            engine,
            "UNIQUE dentro do tenant",
            insert(Order).values(
                tenant_id=scenario.tenant_a_id,
                external_id=scenario.external_id,
                total_cents=scenario.valid_total_cents,
                status=scenario.valid_status,
            ),
        ),
    )

    with engine.begin() as connection:
        connection.execute(
            insert(Order).values(
                tenant_id=scenario.tenant_b_id,
                external_id=scenario.external_id,
                total_cents=scenario.valid_total_cents,
                status=scenario.valid_status,
            )
        )
        count = connection.scalar(
            select(func.count()).select_from(Order).where(Order.external_id == scenario.external_id)
        )

    return ExperimentResult(
        violations=violations,
        same_external_id_across_tenants=count or 0,
    )
