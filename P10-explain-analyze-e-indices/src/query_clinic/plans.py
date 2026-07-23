from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

EXPLAIN_DOCUMENTS = TypeAdapter(list[object])


class PlanNode(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    node_type: str = Field(alias="Node Type")
    relation_name: str | None = Field(default=None, alias="Relation Name")
    index_name: str | None = Field(default=None, alias="Index Name")
    index_condition: str | None = Field(default=None, alias="Index Cond")
    filter_condition: str | None = Field(default=None, alias="Filter")
    sort_key: list[str] = Field(default_factory=list, alias="Sort Key")
    actual_rows: float = Field(alias="Actual Rows")
    actual_loops: float = Field(alias="Actual Loops")
    actual_total_time: float = Field(alias="Actual Total Time")
    plan_rows: float = Field(alias="Plan Rows")
    plan_width: int = Field(alias="Plan Width")
    rows_removed_by_filter: float = Field(default=0, alias="Rows Removed by Filter")
    heap_fetches: int | None = Field(default=None, alias="Heap Fetches")
    shared_hit_blocks: int = Field(default=0, alias="Shared Hit Blocks")
    shared_read_blocks: int = Field(default=0, alias="Shared Read Blocks")
    temp_read_blocks: int = Field(default=0, alias="Temp Read Blocks")
    temp_written_blocks: int = Field(default=0, alias="Temp Written Blocks")
    children: list[object] = Field(default=[], alias="Plans")

    def child_nodes(self) -> list[PlanNode]:
        return [PlanNode.model_validate(child) for child in self.children]


class ExplainResult(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    plan: PlanNode = Field(alias="Plan")
    planning_time_ms: float = Field(alias="Planning Time")
    execution_time_ms: float = Field(alias="Execution Time")

    def nodes(self) -> Iterator[PlanNode]:
        pending = [self.plan]
        while pending:
            node = pending.pop(0)
            yield node
            pending[0:0] = node.child_nodes()

    def scan_types(self) -> list[str]:
        return [node.node_type for node in self.nodes() if "Scan" in node.node_type]


def parse_explain(raw: object) -> ExplainResult:
    documents = EXPLAIN_DOCUMENTS.validate_python(raw)
    if len(documents) != 1:
        raise ValueError("EXPLAIN JSON deveria conter exatamente um documento")
    return ExplainResult.model_validate(documents[0])


def render_explain(result: ExplainResult) -> str:
    lines = [
        "EXPLAIN (ANALYZE, BUFFERS)",
        f"Planning Time: {result.planning_time_ms:.3f} ms",
        f"Execution Time: {result.execution_time_ms:.3f} ms",
        "Plan:",
    ]
    lines.extend(_render_node(result.plan))
    return "\n".join(lines) + "\n"


def _render_node(node: PlanNode, depth: int = 0) -> list[str]:
    indent = "  " * depth
    identity = node.node_type
    if node.relation_name:
        identity += f" on {node.relation_name}"
    if node.index_name:
        identity += f" using {node.index_name}"

    lines = [
        (
            f"{indent}{identity} "
            f"(actual rows={node.actual_rows:g} loops={node.actual_loops:g} "
            f"time={node.actual_total_time:.3f} ms; "
            f"estimated rows={node.plan_rows:g} width={node.plan_width})"
        )
    ]
    if node.index_condition:
        lines.append(f"{indent}  Index Cond: {node.index_condition}")
    if node.filter_condition:
        lines.append(f"{indent}  Filter: {node.filter_condition}")
    if node.sort_key:
        lines.append(f"{indent}  Sort Key: {', '.join(node.sort_key)}")
    if node.rows_removed_by_filter:
        lines.append(f"{indent}  Rows Removed by Filter: {node.rows_removed_by_filter:g}")
    if node.heap_fetches is not None:
        lines.append(f"{indent}  Heap Fetches: {node.heap_fetches}")

    lines.append(
        f"{indent}  Buffers: shared hit={node.shared_hit_blocks} "
        f"read={node.shared_read_blocks}; temp read={node.temp_read_blocks} "
        f"written={node.temp_written_blocks}"
    )
    for child in node.child_nodes():
        lines.extend(_render_node(child, depth + 1))
    return lines
