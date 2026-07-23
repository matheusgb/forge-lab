from pathlib import Path

from tenant_guard import (
    Observation,
    apply_schema,
    create_single_connection_pool,
    load_scenario,
    observe_without_context,
    probe_rollback_cleanup,
    read_with_session_context,
    read_with_transaction_context,
    role_safety,
    seed_documents,
)

ADMIN_DSN = "postgresql://postgres:postgres@127.0.0.1:55441/tenant_lab"
APP_DSN = "postgresql://tenant_app:tenant_app@127.0.0.1:55441/tenant_lab"
ROOT = Path(__file__).resolve().parents[1]


def describe(label: str, observation: Observation) -> list[str]:
    tenant = str(observation.active_tenant) if observation.active_tenant else "nenhum"
    documents = ", ".join(observation.visible_documents) or "nenhum"
    return [
        label,
        f"  conexão física: backend PID {observation.backend_pid}",
        f"  tenant ativo: {tenant}",
        f"  documentos visíveis: {documents}",
    ]


def main() -> None:
    scenario = load_scenario(ROOT / "scenario.yaml")
    tenant_a, tenant_b = scenario.tenants[:2]
    apply_schema(ADMIN_DSN, ROOT / "sql" / "001_schema.sql")
    seed_documents(ADMIN_DSN, scenario.tenants)

    lines = [
        "P11: tenant preso à conexão certa",
        "consulta: SELECT ... FROM documents (sem WHERE tenant_id)",
        "",
    ]
    pool = create_single_connection_pool(APP_DSN)
    try:
        safety = role_safety(pool)
        lines.append(
            "role da aplicação: "
            f"{safety.role}, superuser={safety.is_superuser}, "
            f"bypassrls={safety.bypasses_rls}"
        )
        lines.extend(["", "[INSEGURO: contexto de sessão]"])
        unsafe = read_with_session_context(pool, tenant_a.id)
        leaked = observe_without_context(pool)
        lines.extend(describe(f"requisição de {tenant_a.name}", unsafe))
        lines.extend(describe(f"requisição de {tenant_b.name} sem configurar contexto", leaked))
        lines.append(f"mesma conexão física: {unsafe.backend_pid == leaked.backend_pid}")
        lines.append(f"vazamento reproduzido: {leaked.active_tenant == tenant_a.id}")

        lines.extend(["", "[SEGURO: limpeza do legado e SET LOCAL]"])
        first = read_with_transaction_context(pool, tenant_a.id)
        no_context = observe_without_context(pool)
        second = read_with_transaction_context(pool, tenant_b.id)
        lines.extend(describe(f"requisição de {tenant_a.name}", first))
        lines.extend(describe("consulta seguinte sem contexto", no_context))
        lines.extend(describe(f"requisição de {tenant_b.name}", second))
        lines.append(
            "mesma conexão física nas três consultas: "
            f"{len({first.backend_pid, no_context.backend_pid, second.backend_pid}) == 1}"
        )
        lines.append(f"sem contexto, RLS retornou zero linhas: {not no_context.visible_documents}")

        during_rollback, after_rollback = probe_rollback_cleanup(pool, tenant_a.id)
        lines.extend(["", "[ROLLBACK]"])
        lines.extend(describe("durante a transação", during_rollback))
        lines.extend(describe("depois do rollback", after_rollback))
        lines.append(
            "rollback limpou o contexto: "
            f"{after_rollback.active_tenant is None and not after_rollback.visible_documents}"
        )
    finally:
        pool.close()

    report = "\n".join(lines) + "\n"
    (ROOT / "evidence" / "result.txt").write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
