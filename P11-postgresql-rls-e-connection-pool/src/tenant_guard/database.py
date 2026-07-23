from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import psycopg
from psycopg import Connection, sql
from psycopg_pool import ConnectionPool

from tenant_guard.scenario import Tenant

type Row = tuple[Any, ...]
type DatabaseConnection = Connection[Row]
type DatabasePool = ConnectionPool[DatabaseConnection]

_VISIBLE_DOCUMENTS_SQL = """
    SELECT
        pg_backend_pid(),
        NULLIF(current_setting('app.tenant_id', true), ''),
        COALESCE(array_agg(title ORDER BY title), ARRAY[]::text[])
    FROM documents
"""


@dataclass(frozen=True, slots=True)
class Observation:
    backend_pid: int
    active_tenant: UUID | None
    visible_documents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleSafety:
    role: str
    is_superuser: bool
    bypasses_rls: bool


def create_single_connection_pool(dsn: str) -> DatabasePool:
    pool: DatabasePool = ConnectionPool(
        conninfo=dsn,
        min_size=1,
        max_size=1,
        open=False,
    )
    pool.open(wait=True)
    return pool


def apply_schema(admin_dsn: str, schema_path: Path) -> None:
    schema = schema_path.read_text(encoding="utf-8")
    trusted_schema = sql.SQL(schema)  # pyright: ignore[reportArgumentType]
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(trusted_schema)


def seed_documents(admin_dsn: str, tenants: Iterable[Tenant]) -> None:
    rows = [(tenant.id, title) for tenant in tenants for title in tenant.documents]
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute("TRUNCATE documents RESTART IDENTITY")
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO documents (tenant_id, title) VALUES (%s, %s)",
                rows,
            )


def read_with_session_context(pool: DatabasePool, tenant_id: UUID) -> Observation:
    """Versão insegura: o valor sobrevive ao commit e volta ao pool."""
    with pool.connection() as connection, connection.transaction():
        connection.execute(
            "SELECT set_config('app.tenant_id', %s, false)",
            (str(tenant_id),),
        )
        return _observe(connection)


def read_with_transaction_context(pool: DatabasePool, tenant_id: UUID) -> Observation:
    """Versão segura: limpa o legado e limita o novo valor à transação."""
    with tenant_transaction(pool, tenant_id) as connection:
        return _observe(connection)


@contextmanager
def tenant_transaction(
    pool: DatabasePool,
    tenant_id: UUID,
) -> Generator[DatabaseConnection]:
    with pool.connection() as connection:
        with connection.transaction():
            connection.execute(
                "SELECT set_config('app.tenant_id', '', false)",
            )
        with connection.transaction():
            connection.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                (str(tenant_id),),
            )
            yield connection


class _RollbackProbe(Exception):
    pass


def probe_rollback_cleanup(
    pool: DatabasePool,
    tenant_id: UUID,
) -> tuple[Observation, Observation]:
    during: Observation | None = None
    try:
        with tenant_transaction(pool, tenant_id) as connection:
            during = _observe(connection)
            raise _RollbackProbe
    except _RollbackProbe:
        pass
    if during is None:
        raise AssertionError("a observação antes do rollback não foi executada")
    return during, observe_without_context(pool)


def observe_without_context(pool: DatabasePool) -> Observation:
    with pool.connection() as connection, connection.transaction():
        return _observe(connection)


def role_safety(pool: DatabasePool) -> RoleSafety:
    with pool.connection() as connection, connection.transaction():
        row = connection.execute(
            """
            SELECT rolname, rolsuper, rolbypassrls
            FROM pg_roles
            WHERE rolname = current_user
            """
        ).fetchone()
    if row is None:
        raise RuntimeError("application role was not found")
    return RoleSafety(
        role=cast(str, row[0]),
        is_superuser=cast(bool, row[1]),
        bypasses_rls=cast(bool, row[2]),
    )


def _observe(connection: DatabaseConnection) -> Observation:
    row = connection.execute(_VISIBLE_DOCUMENTS_SQL).fetchone()
    if row is None:
        raise RuntimeError("observation query returned no row")

    active_tenant = cast(str | None, row[1])
    documents = cast(list[str], row[2])
    return Observation(
        backend_pid=cast(int, row[0]),
        active_tenant=UUID(active_tenant) if active_tenant else None,
        visible_documents=tuple(documents),
    )
