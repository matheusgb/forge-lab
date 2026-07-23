import pytest

from query_clinic.plans import parse_explain, render_explain


def sample_explain() -> list[object]:
    return [
        {
            "Plan": {
                "Node Type": "Limit",
                "Plan Rows": 50,
                "Plan Width": 32,
                "Actual Rows": 50,
                "Actual Loops": 1,
                "Actual Total Time": 0.2,
                "Shared Hit Blocks": 4,
                "Plans": [
                    {
                        "Node Type": "Index Only Scan",
                        "Relation Name": "orders",
                        "Index Name": "idx_orders_tenant_status_created",
                        "Index Cond": "((tenant_id = 7) AND (status = 'pending'::text))",
                        "Plan Rows": 120,
                        "Plan Width": 32,
                        "Actual Rows": 50,
                        "Actual Loops": 1,
                        "Actual Total Time": 0.18,
                        "Shared Hit Blocks": 4,
                        "Heap Fetches": 0,
                    }
                ],
            },
            "Planning Time": 0.15,
            "Execution Time": 0.25,
        }
    ]


def test_plan_exposes_scan_chosen_by_postgres() -> None:
    result = parse_explain(sample_explain())

    assert result.scan_types() == ["Index Only Scan"]
    assert result.execution_time_ms == 0.25


def test_render_keeps_condition_buffers_and_heap_fetches_visible() -> None:
    rendered = render_explain(parse_explain(sample_explain()))

    assert "Index Only Scan on orders using idx_orders_tenant_status_created" in rendered
    assert "Index Cond: ((tenant_id = 7) AND (status = 'pending'::text))" in rendered
    assert "Buffers: shared hit=4 read=0" in rendered
    assert "Heap Fetches: 0" in rendered


def test_parser_rejects_unexpected_document_count() -> None:
    with pytest.raises(ValueError, match="exatamente um documento"):
        parse_explain([])
