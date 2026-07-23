"""Demonstra contexto de tenant seguro em um pool PostgreSQL."""

from tenant_guard.database import (
    Observation,
    RoleSafety,
    apply_schema,
    create_single_connection_pool,
    observe_without_context,
    probe_rollback_cleanup,
    read_with_session_context,
    read_with_transaction_context,
    role_safety,
    seed_documents,
    tenant_transaction,
)
from tenant_guard.scenario import Scenario, Tenant, load_scenario

__all__ = [
    "Observation",
    "RoleSafety",
    "Scenario",
    "Tenant",
    "apply_schema",
    "create_single_connection_pool",
    "load_scenario",
    "observe_without_context",
    "probe_rollback_cleanup",
    "read_with_session_context",
    "read_with_transaction_context",
    "role_safety",
    "seed_documents",
    "tenant_transaction",
]
