import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect

from schema_guard.experiment import run_constraint_probes
from schema_guard.migrations import downgrade, upgrade
from schema_guard.scenario import Scenario


@pytest.fixture
def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if value is None:
        pytest.skip("defina DATABASE_URL para executar os testes PostgreSQL")
    return value


@pytest.fixture
def migrated_engine(database_url: str) -> Iterator[Engine]:
    downgrade(database_url)
    upgrade(database_url)
    engine = create_engine(database_url)
    yield engine
    engine.dispose()
    downgrade(database_url)


@pytest.mark.integration
def test_postgres_rejects_every_invalid_write(
    migrated_engine: Engine,
    scenario: Scenario,
) -> None:
    result = run_constraint_probes(migrated_engine, scenario)

    assert [item.database_error for item in result.violations] == [
        "ForeignKeyViolation",
        "NotNullViolation",
        "CheckViolation",
        "UniqueViolation",
    ]
    assert result.same_external_id_across_tenants == 2


@pytest.mark.integration
def test_migration_runs_down_and_up_again(database_url: str) -> None:
    engine = create_engine(database_url)
    downgrade(database_url)
    upgrade(database_url)
    assert inspect(engine).has_table("orders")

    downgrade(database_url)
    assert not inspect(engine).has_table("orders")

    upgrade(database_url)
    assert inspect(engine).has_table("orders")
    engine.dispose()
