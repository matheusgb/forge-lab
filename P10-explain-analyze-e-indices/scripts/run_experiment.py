import json
from pathlib import Path

from query_clinic.config import load_scenario
from query_clinic.database import (
    collect_index_plans,
    compare_access_patterns,
    connect,
    reset_and_seed,
    server_version,
)
from query_clinic.plans import ExplainResult, render_explain

ROOT = Path(__file__).resolve().parents[1]
PLAN_LABELS = {
    "sem_indice": "Sem índice",
    "indice_inadequado": "Índice apenas em status",
    "sequential_scan_legitimo": "Sequential scan legítimo",
    "indice_composto_alinhado": "Índice composto alinhado",
}


def main() -> None:
    scenario = load_scenario(ROOT / "scenario.yaml")
    evidence_dir = ROOT / "evidence"
    plans_dir = evidence_dir / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    print("Preparando o conjunto determinístico no PostgreSQL...")
    with connect(scenario.dsn) as conn:
        version = server_version(conn)
        reset_and_seed(conn, scenario)
        plans = collect_index_plans(conn, scenario.target)
        access = compare_access_patterns(conn, scenario.target)

    for name, plan in plans.items():
        (plans_dir / f"{name}.txt").write_text(render_explain(plan), encoding="utf-8")
        (plans_dir / f"{name}.json").write_text(
            json.dumps(plan.model_dump(by_alias=True), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    report = _report(version, scenario.seed.row_count, plans, access.model_dump())
    (evidence_dir / "result.txt").write_text(report, encoding="utf-8")
    print(report, end="")


def _report(
    version: str,
    row_count: int,
    plans: dict[str, ExplainResult],
    access: dict[str, object],
) -> str:
    lines = [
        "P10: clínica do plano de consulta",
        f"PostgreSQL: {version}",
        f"Linhas em orders: {row_count}",
        "",
        "Planos medidos com EXPLAIN (ANALYZE, BUFFERS):",
    ]
    for name, plan in plans.items():
        scans = ", ".join(plan.scan_types()) or "nenhum scan"
        lines.append(
            f"- {PLAN_LABELS[name]}: {scans}; execução={plan.execution_time_ms:.3f} ms; "
            f"buffers hit={plan.plan.shared_hit_blocks}, read={plan.plan.shared_read_blocks}"
        )

    lines.extend(
        [
            "",
            "Acesso da aplicação:",
            f"- Linhas lógicas: {access['logical_rows']}",
            f"- N+1: {access['n_plus_one_queries']} consultas",
            f"- JOIN: {access['join_queries']} consulta",
            f"- Mesmo resultado lógico: {str(access['logical_results_equal']).lower()}",
            (
                "- Projeção mínima: "
                f"{access['minimal_projection_bytes']} bytes na serialização JSON local"
            ),
            (f"- SELECT amplo: {access['wide_projection_bytes']} bytes na serialização JSON local"),
            "",
            "Os tempos e buffers pertencem somente a esta execução local.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
