from collections.abc import Iterator

import pytest
from psycopg.errors import InsufficientPrivilege

from tenant_guard import (
    Scenario,
    create_single_connection_pool,
    observe_without_context,
    probe_rollback_cleanup,
    read_with_session_context,
    read_with_transaction_context,
    role_safety,
)
from tenant_guard.database import DatabasePool

APP_DSN = "postgresql://tenant_app:tenant_app@127.0.0.1:55441/tenant_lab"


@pytest.fixture
def pool() -> Iterator[DatabasePool]:
    database_pool = create_single_connection_pool(APP_DSN)
    yield database_pool
    database_pool.close()


def test_session_context_leaks_when_connection_returns_to_pool(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    tenant_a = scenario.tenants[0]

    first_request = read_with_session_context(pool, tenant_a.id)
    next_request_without_context = observe_without_context(pool)

    assert next_request_without_context.backend_pid == first_request.backend_pid
    assert next_request_without_context.active_tenant == tenant_a.id
    assert next_request_without_context.visible_documents == tuple(sorted(tenant_a.documents))


def test_transaction_context_disappears_before_connection_is_reused(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    tenant_a = scenario.tenants[0]

    first_request = read_with_transaction_context(pool, tenant_a.id)
    next_request_without_context = observe_without_context(pool)

    assert next_request_without_context.backend_pid == first_request.backend_pid
    assert next_request_without_context.active_tenant is None
    assert next_request_without_context.visible_documents == ()


def test_safe_boundary_removes_a_legacy_session_value(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    tenant_a, tenant_b = scenario.tenants[:2]

    contaminated = read_with_session_context(pool, tenant_a.id)
    safe_request = read_with_transaction_context(pool, tenant_b.id)
    next_request_without_context = observe_without_context(pool)

    assert (
        len(
            {
                contaminated.backend_pid,
                safe_request.backend_pid,
                next_request_without_context.backend_pid,
            }
        )
        == 1
    )
    assert safe_request.visible_documents == tuple(sorted(tenant_b.documents))
    assert next_request_without_context.active_tenant is None
    assert next_request_without_context.visible_documents == ()


def test_transaction_context_disappears_after_rollback(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    during, after = probe_rollback_cleanup(pool, scenario.tenants[0].id)

    assert during.backend_pid == after.backend_pid
    assert during.active_tenant == scenario.tenants[0].id
    assert after.active_tenant is None
    assert after.visible_documents == ()


def test_rls_isolates_queries_without_tenant_filter(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    tenant_a, tenant_b = scenario.tenants[:2]

    visible_to_a = read_with_transaction_context(pool, tenant_a.id)
    visible_to_b = read_with_transaction_context(pool, tenant_b.id)

    assert visible_to_a.visible_documents == tuple(sorted(tenant_a.documents))
    assert visible_to_b.visible_documents == tuple(sorted(tenant_b.documents))
    assert visible_to_a.backend_pid == visible_to_b.backend_pid


def test_application_role_cannot_bypass_rls(pool: DatabasePool) -> None:
    safety = role_safety(pool)

    assert safety.role == "tenant_app"
    assert safety.is_superuser is False
    assert safety.bypasses_rls is False


def test_rls_rejects_cross_tenant_insert(
    pool: DatabasePool,
    scenario: Scenario,
) -> None:
    tenant_a, tenant_b = scenario.tenants[:2]

    with (
        pytest.raises(InsufficientPrivilege),
        pool.connection() as connection,
        connection.transaction(),
    ):
        connection.execute(
            "SELECT set_config('app.tenant_id', %s, true)",
            (str(tenant_a.id),),
        )
        connection.execute(
            "INSERT INTO documents (tenant_id, title) VALUES (%s, %s)",
            (tenant_b.id, "invasao.txt"),
        )
