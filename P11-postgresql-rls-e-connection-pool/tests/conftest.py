from collections.abc import Iterator
from pathlib import Path

import pytest
from psycopg import OperationalError

from tenant_guard import Scenario, apply_schema, load_scenario, seed_documents

ADMIN_DSN = "postgresql://postgres:postgres@127.0.0.1:55441/tenant_lab"
APP_DSN = "postgresql://tenant_app:tenant_app@127.0.0.1:55441/tenant_lab"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def scenario() -> Scenario:
    return load_scenario(ROOT / "scenario.yaml")


@pytest.fixture(scope="session", autouse=True)
def current_schema() -> None:
    try:
        apply_schema(ADMIN_DSN, ROOT / "sql" / "001_schema.sql")
    except OperationalError as error:
        pytest.fail(
            "PostgreSQL indisponível. Execute `docker compose up -d --wait` antes dos testes. "
            f"Detalhe: {error}"
        )


@pytest.fixture(autouse=True)
def clean_database(current_schema: None, scenario: Scenario) -> Iterator[None]:
    seed_documents(ADMIN_DSN, scenario.tenants)
    yield
