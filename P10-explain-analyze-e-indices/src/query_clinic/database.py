import json
from typing import Any, LiteralString

import psycopg
from psycopg import Connection, sql
from pydantic import BaseModel

from query_clinic.config import Scenario, TargetConfig
from query_clinic.plans import ExplainResult, parse_explain

type DbConnection = Connection[tuple[Any, ...]]

TARGET_QUERY: LiteralString = """
SELECT id, customer_id, created_at, total_cents
FROM query_clinic.orders
WHERE tenant_id = %s AND status = %s
ORDER BY created_at DESC
LIMIT %s
"""

LEGITIMATE_SEQUENTIAL_SCAN: LiteralString = """
SELECT sum(total_cents)
FROM query_clinic.orders
WHERE status = 'completed'
"""


class AccessComparison(BaseModel):
    logical_rows: int
    logical_results_equal: bool
    n_plus_one_queries: int
    join_queries: int
    minimal_projection_bytes: int
    wide_projection_bytes: int


def connect(database_url: str) -> DbConnection:
    return psycopg.connect(database_url, autocommit=True)


def server_version(conn: DbConnection) -> str:
    row = conn.execute("SELECT version()").fetchone()
    if row is None:
        raise RuntimeError("PostgreSQL não retornou a versão")
    return str(row[0])


def reset_and_seed(conn: DbConnection, scenario: Scenario) -> None:
    conn.execute("SET max_parallel_workers_per_gather = 0")
    conn.execute("DROP SCHEMA IF EXISTS query_clinic CASCADE")
    conn.execute("CREATE SCHEMA query_clinic")
    conn.execute(
        """
        CREATE TABLE query_clinic.customers (
            id integer PRIMARY KEY,
            name text NOT NULL,
            segment text NOT NULL,
            profile jsonb NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE query_clinic.orders (
            id bigint PRIMARY KEY,
            tenant_id integer NOT NULL,
            customer_id integer NOT NULL REFERENCES query_clinic.customers(id),
            status text NOT NULL CHECK (status IN ('pending', 'completed')),
            created_at timestamptz NOT NULL,
            total_cents integer NOT NULL CHECK (total_cents > 0),
            notes text NOT NULL,
            metadata jsonb NOT NULL
        )
        """
    )

    seed = scenario.seed
    conn.execute(
        """
        INSERT INTO query_clinic.customers (id, name, segment, profile)
        SELECT
            n,
            'customer-' || lpad(n::text, 4, '0'),
            CASE WHEN n %% 5 = 0 THEN 'enterprise' ELSE 'standard' END,
            jsonb_build_object('region', 'br-' || (n %% 5), 'reference', md5(n::text))
        FROM generate_series(1, %s) AS generated(n)
        """,
        (seed.customer_count,),
    )
    conn.execute(
        """
        INSERT INTO query_clinic.orders (
            id, tenant_id, customer_id, status, created_at,
            total_cents, notes, metadata
        )
        SELECT
            n,
            1 + ((n - 1) %% %s),
            1 + (((n - 1) * 17) %% %s),
            CASE
                WHEN (((n - 1) / %s) %% %s) = 0 THEN 'pending'
                ELSE 'completed'
            END,
            timestamptz '2025-01-01 00:00:00+00' + n * interval '1 second',
            100 + ((n * 97) %% 100000),
            repeat(md5(n::text), 8),
            jsonb_build_object(
                'source', 'deterministic-seed',
                'external_id', md5((n * 31)::text),
                'attempt', n %% 3
            )
        FROM generate_series(1, %s) AS generated(n)
        """,
        (
            seed.tenant_count,
            seed.customer_count,
            seed.tenant_count,
            seed.pending_every,
            seed.row_count,
        ),
    )
    conn.execute("VACUUM (ANALYZE) query_clinic.orders")


def collect_index_plans(conn: DbConnection, target: TargetConfig) -> dict[str, ExplainResult]:
    _drop_optional_indexes(conn)
    conn.execute("ANALYZE query_clinic.orders")
    without_index = _explain(conn, TARGET_QUERY, _target_params(target))

    conn.execute("CREATE INDEX idx_orders_status ON query_clinic.orders (status)")
    conn.execute("ANALYZE query_clinic.orders")
    inadequate_index = _explain(conn, TARGET_QUERY, _target_params(target))
    legitimate_sequential = _explain(conn, LEGITIMATE_SEQUENTIAL_SCAN)

    conn.execute("DROP INDEX query_clinic.idx_orders_status")
    conn.execute(
        """
        CREATE INDEX idx_orders_tenant_status_created
        ON query_clinic.orders (tenant_id, status, created_at DESC)
        INCLUDE (id, customer_id, total_cents)
        """
    )
    conn.execute("ANALYZE query_clinic.orders")
    aligned_index = _explain(conn, TARGET_QUERY, _target_params(target))

    return {
        "sem_indice": without_index,
        "indice_inadequado": inadequate_index,
        "sequential_scan_legitimo": legitimate_sequential,
        "indice_composto_alinhado": aligned_index,
    }


def compare_access_patterns(conn: DbConnection, target: TargetConfig) -> AccessComparison:
    params = (target.tenant_id, target.status, target.n_plus_one_rows)
    orders = conn.execute(
        """
        SELECT id, customer_id, created_at, total_cents
        FROM query_clinic.orders
        WHERE tenant_id = %s AND status = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        params,
    ).fetchall()

    assembled: list[tuple[object, ...]] = []
    query_count = 1
    for order_id, customer_id, created_at, total_cents in orders:
        customer = conn.execute(
            "SELECT name FROM query_clinic.customers WHERE id = %s",
            (customer_id,),
        ).fetchone()
        query_count += 1
        if customer is None:
            raise RuntimeError(f"cliente {customer_id} não encontrado")
        assembled.append((order_id, created_at, total_cents, customer[0]))

    joined = conn.execute(
        """
        SELECT o.id, o.created_at, o.total_cents, c.name
        FROM query_clinic.orders AS o
        JOIN query_clinic.customers AS c ON c.id = o.customer_id
        WHERE o.tenant_id = %s AND o.status = %s
        ORDER BY o.created_at DESC
        LIMIT %s
        """,
        params,
    ).fetchall()

    wide = conn.execute(
        """
        SELECT o.*, c.*
        FROM query_clinic.orders AS o
        JOIN query_clinic.customers AS c ON c.id = o.customer_id
        WHERE o.tenant_id = %s AND o.status = %s
        ORDER BY o.created_at DESC
        LIMIT %s
        """,
        params,
    ).fetchall()

    return AccessComparison(
        logical_rows=len(joined),
        logical_results_equal=assembled == joined,
        n_plus_one_queries=query_count,
        join_queries=1,
        minimal_projection_bytes=_serialized_bytes(joined),
        wide_projection_bytes=_serialized_bytes(wide),
    )


def _drop_optional_indexes(conn: DbConnection) -> None:
    conn.execute("DROP INDEX IF EXISTS query_clinic.idx_orders_status")
    conn.execute("DROP INDEX IF EXISTS query_clinic.idx_orders_tenant_status_created")


def _target_params(target: TargetConfig) -> tuple[object, ...]:
    return (target.tenant_id, target.status, target.page_size)


def _explain(
    conn: DbConnection,
    query: LiteralString,
    params: tuple[object, ...] = (),
) -> ExplainResult:
    row = conn.execute(
        sql.SQL("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ") + sql.SQL(query),
        params,
    ).fetchone()
    if row is None:
        raise RuntimeError("EXPLAIN não retornou um plano")
    return parse_explain(row[0])


def _serialized_bytes(rows: list[tuple[Any, ...]]) -> int:
    payload = json.dumps(rows, default=str, ensure_ascii=False, separators=(",", ":"))
    return len(payload.encode("utf-8"))
