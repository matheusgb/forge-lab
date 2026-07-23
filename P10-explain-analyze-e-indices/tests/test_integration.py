import os
from pathlib import Path

import pytest

from query_clinic.config import load_scenario
from query_clinic.database import (
    collect_index_plans,
    compare_access_patterns,
    connect,
    reset_and_seed,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_INTEGRATION = os.getenv("P10_RUN_INTEGRATION") == "1"


@pytest.mark.integration
@pytest.mark.skipif(
    not RUN_INTEGRATION, reason="defina P10_RUN_INTEGRATION=1 com o container ativo"
)
def test_real_plans_and_access_patterns() -> None:
    scenario = load_scenario(ROOT / "scenario.yaml")

    with connect(scenario.dsn) as conn:
        reset_and_seed(conn, scenario)
        plans = collect_index_plans(conn, scenario.target)
        access = compare_access_patterns(conn, scenario.target)

    assert "Seq Scan" in plans["sem_indice"].scan_types()
    inadequate_nodes = tuple(plans["indice_inadequado"].nodes())
    assert any(node.index_name == "idx_orders_status" for node in inadequate_nodes)
    assert any(node.node_type == "Sort" for node in inadequate_nodes)
    assert sum(node.rows_removed_by_filter for node in inadequate_nodes) > 0
    assert "Index Only Scan" in plans["indice_composto_alinhado"].scan_types()
    assert "Seq Scan" in plans["sequential_scan_legitimo"].scan_types()
    assert access.logical_results_equal
    assert access.n_plus_one_queries == scenario.target.n_plus_one_rows + 1
    assert access.join_queries == 1
    assert access.wide_projection_bytes > access.minimal_projection_bytes
