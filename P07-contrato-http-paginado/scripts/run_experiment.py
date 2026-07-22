import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from paginated_contract.client import OffsetPaginatedClient, PaginatedClient
from paginated_contract.errors import ContractError, CursorLoopError
from paginated_contract.feed import MutableCommentFeed, ScriptedProvider
from paginated_contract.model import Comment


@dataclass(frozen=True)
class Scenario:
    name: str
    page_size: int
    initial_comment_ids: tuple[int, ...]
    insert_after_page: int
    new_comment_id: int


def load_scenario(path: Path) -> Scenario:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    raw_ids = cast(list[int], raw["initial_comment_ids"])
    return Scenario(
        name=str(raw["name"]),
        page_size=cast(int, raw["page_size"]),
        initial_comment_ids=tuple(raw_ids),
        insert_after_page=cast(int, raw["insert_after_page"]),
        new_comment_id=cast(int, raw["new_comment_id"]),
    )


def make_comment(comment_id: int) -> Comment:
    return Comment(
        id=comment_id,
        body=f"Comentário {comment_id}",
        created_at=f"2026-07-22T12:{comment_id:02d}:00Z",
    )


def build_feed(scenario: Scenario) -> MutableCommentFeed:
    return MutableCommentFeed(
        comments=tuple(make_comment(comment_id) for comment_id in scenario.initial_comment_ids),
        page_size=scenario.page_size,
    )


def insert_new_comment(feed: MutableCommentFeed, scenario: Scenario, page_number: int) -> None:
    if page_number == scenario.insert_after_page:
        feed.add_comment(make_comment(scenario.new_comment_id))


def compatible_contract_result() -> tuple[int, ...]:
    provider = ScriptedProvider(
        {
            None: {
                "items": [
                    {
                        "id": 1,
                        "body": "Contrato v2",
                        "created_at": "2026-07-22T12:01:00Z",
                        "author_badge": "top contributor",
                    }
                ],
                "next_cursor": None,
                "api_version": "2",
            }
        }
    )
    return PaginatedClient(provider).fetch_all().ids


def incompatible_contract_error() -> str:
    provider = ScriptedProvider(
        {
            None: {
                "items": [
                    {
                        "id": 1,
                        "text": "Campo body foi renomeado",
                        "created_at": "2026-07-22T12:01:00Z",
                    }
                ],
                "next_cursor": None,
            }
        }
    )
    try:
        PaginatedClient(provider).fetch_all()
    except ContractError as error:
        return str(error)
    raise AssertionError("o contrato incompatível deveria falhar")


def cursor_loop_error() -> str:
    provider = ScriptedProvider(
        {
            None: {
                "items": [
                    {
                        "id": 2,
                        "body": "Primeira página",
                        "created_at": "2026-07-22T12:02:00Z",
                    }
                ],
                "next_cursor": "loop",
            },
            "loop": {
                "items": [
                    {
                        "id": 1,
                        "body": "Segunda página",
                        "created_at": "2026-07-22T12:01:00Z",
                    }
                ],
                "next_cursor": "loop",
            },
        }
    )
    try:
        PaginatedClient(provider).fetch_all()
    except CursorLoopError as error:
        return str(error)
    raise AssertionError("o loop de cursor deveria falhar")


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")

    baseline = PaginatedClient(build_feed(scenario)).fetch_all()

    offset_feed = build_feed(scenario)
    offset = OffsetPaginatedClient(offset_feed).fetch_all(
        after_page=lambda page: insert_new_comment(offset_feed, scenario, page)
    )

    cursor_feed = build_feed(scenario)
    cursor = PaginatedClient(cursor_feed).fetch_all(
        after_page=lambda page: insert_new_comment(cursor_feed, scenario, page)
    )
    refreshed = PaginatedClient(cursor_feed).fetch_all()

    lines = [
        f"Cenário: {scenario.name}",
        f"Baseline por cursor: páginas={baseline.pages}; itens={baseline.ids}",
        f"OFFSET após inserção: páginas={offset.pages}; itens={offset.ids}",
        f"Cursor após inserção: páginas={cursor.pages}; itens={cursor.ids}",
        f"Nova leitura: primeira página={refreshed.pages[0]}",
        f"Contrato v2 compatível: itens={compatible_contract_result()}",
        f"Contrato incompatível: {incompatible_contract_error()}",
        f"Cursor em loop: {cursor_loop_error()}",
    ]
    output = "\n".join(lines)
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
