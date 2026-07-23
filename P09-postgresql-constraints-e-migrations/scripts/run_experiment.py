import os
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from schema_guard.experiment import run_constraint_probes
from schema_guard.migrations import downgrade, upgrade
from schema_guard.scenario import load_scenario

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "postgresql+psycopg://forge:forge@127.0.0.1:55439/schema_guard"


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    url = make_url(database_url)
    if (
        url.database != "schema_guard"
        or url.host not in {"127.0.0.1", "localhost"}
        or url.port != 55439
        or url.username != "forge"
    ):
        raise SystemExit("O experimento aceita somente forge@localhost:55439/schema_guard.")
    return database_url


def main() -> None:
    database_url = _database_url()
    scenario = load_scenario(PROJECT_ROOT / "scenario.yaml")

    downgrade(database_url)
    upgrade(database_url)

    engine = create_engine(database_url)
    result = run_constraint_probes(engine, scenario)

    print("Constraints observadas pelo PostgreSQL:")
    for violation in result.violations:
        print(f"  {violation.case}: rejeitada com {violation.database_error}")
    print(
        "  UNIQUE por tenant: "
        f"o mesmo external_id existe em {result.same_external_id_across_tenants} tenants"
    )

    downgrade(database_url)
    tables_after_downgrade = any(
        inspect(engine).has_table(table_name) for table_name in ("tenants", "orders")
    )
    upgrade(database_url)
    tables_after_second_upgrade = all(
        inspect(engine).has_table(table_name) for table_name in ("tenants", "orders")
    )
    engine.dispose()

    print("Ciclo da migration:")
    print(f"  downgrade base removeu as tabelas: {not tables_after_downgrade}")
    print(f"  segundo upgrade head recriou as tabelas: {tables_after_second_upgrade}")


if __name__ == "__main__":
    main()
