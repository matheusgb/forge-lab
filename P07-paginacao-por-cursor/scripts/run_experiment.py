import argparse
from datetime import UTC, datetime
from json import dumps
from pathlib import Path
from typing import Never, cast

from pydantic import BaseModel, ConfigDict, PositiveInt

from paginated_contract.client import PaginatedClient
from paginated_contract.errors import ContractError, CursorLoopError
from paginated_contract.feed import MutableCommentFeed, ScriptedProvider
from paginated_contract.model import Comment


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    page_size: PositiveInt
    initial_comment_ids: tuple[int, ...]
    insert_after_page: PositiveInt
    new_comment_id: int


class Arguments(argparse.Namespace):
    step_by_step: bool = False


class TracingProvider:
    def __init__(self, provider: MutableCommentFeed) -> None:
        self._provider = provider
        self._page_number = 0

    def get_page(self, cursor: str | None) -> object:
        self._page_number += 1
        print(f"Página {self._page_number}")
        print(f"Chamada: provider.get_page(cursor={cursor!r})")

        response = self._provider.get_page(cursor)
        print("JSON recebido:")
        print(dumps(response, ensure_ascii=False, indent=2))

        payload = cast(dict[str, object], response)
        next_cursor = payload.get("next_cursor")
        print(f"next_cursor recebido: {dumps(next_cursor, ensure_ascii=False)}")
        if next_cursor is None:
            print("Decisão: o cliente encerra a paginação.")
        else:
            print("Decisão: o cliente envia esse cursor na próxima chamada.")
        print()
        return response


def make_comment(comment_id: int) -> Comment:
    return Comment(
        id=comment_id,
        body=f"Comentário {comment_id}",
        created_at=datetime(2026, 7, 22, 12, comment_id, tzinfo=UTC),
    )


def build_feed(scenario: Scenario, *, schedule_insert: bool = False) -> MutableCommentFeed:
    feed = MutableCommentFeed(
        comments=tuple(make_comment(comment_id) for comment_id in scenario.initial_comment_ids),
        page_size=scenario.page_size,
    )
    if schedule_insert:
        feed.schedule_insert(
            after_page=scenario.insert_after_page,
            comment=make_comment(scenario.new_comment_id),
        )
    return feed


def walk_offset(feed: MutableCommentFeed) -> tuple[tuple[int, ...], ...]:
    offset = 0
    pages: list[tuple[int, ...]] = []
    while True:
        items, next_offset = feed.get_offset_page(offset)
        pages.append(tuple(item.id for item in items))
        if next_offset is None:
            return tuple(pages)
        offset = next_offset


def raw_comment(comment_id: int) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": f"Comentário {comment_id}",
        "created_at": f"2026-07-22T12:{comment_id:02d}:00Z",
    }


def fail(message: str) -> Never:
    raise AssertionError(message)


def load_scenario() -> tuple[Path, Scenario]:
    project = Path(__file__).resolve().parents[1]
    scenario = Scenario.model_validate_json((project / "scenario.yaml").read_text())
    return project, scenario


def contract_results() -> tuple[tuple[int, ...], str, str]:
    compatible = raw_comment(1) | {"author_badge": "top contributor"}
    compatible_ids = (
        PaginatedClient(
            ScriptedProvider(
                {None: {"items": [compatible], "next_cursor": None, "api_version": "2"}}
            )
        )
        .fetch_all()
        .ids
    )

    incompatible = raw_comment(1)
    incompatible["text"] = incompatible.pop("body")
    try:
        PaginatedClient(
            ScriptedProvider({None: {"items": [incompatible], "next_cursor": None}})
        ).fetch_all()
    except ContractError as error:
        incompatible_error = str(error)
    else:
        fail("o contrato incompatível deveria falhar")

    loop_provider = ScriptedProvider(
        {
            None: {"items": [raw_comment(2)], "next_cursor": "loop"},
            "loop": {"items": [raw_comment(1)], "next_cursor": "loop"},
        }
    )
    try:
        PaginatedClient(loop_provider).fetch_all()
    except CursorLoopError as error:
        loop_error = str(error)
    else:
        fail("o cursor repetido deveria falhar")

    return compatible_ids, incompatible_error, loop_error


def run() -> str:
    project, scenario = load_scenario()
    baseline = PaginatedClient(build_feed(scenario)).fetch_all()
    offset = walk_offset(build_feed(scenario, schedule_insert=True))
    cursor_feed = build_feed(scenario, schedule_insert=True)
    cursor = PaginatedClient(cursor_feed).fetch_all()
    refreshed = PaginatedClient(cursor_feed).fetch_all()
    compatible, incompatible, loop = contract_results()

    output = "\n".join(
        [
            f"Cenário: {scenario.name}",
            f"Baseline por cursor: páginas={baseline.pages}; itens={baseline.ids}",
            f"OFFSET após inserção: páginas={offset}",
            f"Cursor após inserção: páginas={cursor.pages}; itens={cursor.ids}",
            f"Nova leitura: primeira página={refreshed.pages[0]}",
            f"Contrato v2 compatível: itens={compatible}",
            f"Contrato incompatível: {incompatible}",
            f"Cursor em loop: {loop}",
        ]
    )
    (project / "evidence" / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


def run_step_by_step() -> str:
    _, scenario = load_scenario()
    print(f"Cenário: {scenario.name}")
    print("Entrada: PaginatedClient(provider).fetch_all()")
    print("O cliente começa a primeira chamada com cursor=None.")
    print(
        f"Durante a leitura, o comentário {scenario.new_comment_id} será inserido "
        f"depois da página {scenario.insert_after_page}."
    )
    print()

    provider = TracingProvider(build_feed(scenario, schedule_insert=True))
    result = PaginatedClient(provider).fetch_all()
    return f"Resultado final: páginas={result.pages}; itens={result.ids}"


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description="Executa o experimento de paginação do P07.")
    parser.add_argument(
        "--step-by-step",
        action="store_true",
        help="mostra cada chamada, o JSON recebido e o cursor da próxima página",
    )
    arguments = Arguments()
    parser.parse_args(namespace=arguments)
    return arguments


def main() -> None:
    arguments = parse_arguments()
    output = run_step_by_step() if arguments.step_by_step else run()
    print(output)


if __name__ == "__main__":
    main()
