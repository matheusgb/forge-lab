import pytest

from paginated_contract.client import PaginatedClient
from paginated_contract.errors import ContractError, CursorLoopError
from paginated_contract.feed import ScriptedProvider


def raw_comment(comment_id: int) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": f"Comentário {comment_id}",
        "created_at": f"2026-07-22T12:{comment_id:02d}:00Z",
    }


def test_client_walks_all_pages_in_order() -> None:
    provider = ScriptedProvider(
        {
            None: {"items": [raw_comment(6), raw_comment(5)], "next_cursor": "p2"},
            "p2": {"items": [raw_comment(4), raw_comment(3)], "next_cursor": "p3"},
            "p3": {"items": [raw_comment(2), raw_comment(1)], "next_cursor": None},
        }
    )

    result = PaginatedClient(provider).fetch_all()

    assert result.ids == (6, 5, 4, 3, 2, 1)
    assert result.pages == ((6, 5), (4, 3), (2, 1))
    assert provider.calls == [None, "p2", "p3"]


def test_terminal_empty_page_is_valid() -> None:
    provider = ScriptedProvider({None: {"items": [], "next_cursor": None}})

    result = PaginatedClient(provider).fetch_all()

    assert result.items == ()
    assert result.pages == ((),)


def test_empty_page_cannot_point_to_another_page() -> None:
    provider = ScriptedProvider({None: {"items": [], "next_cursor": "p2"}})

    with pytest.raises(ContractError, match="página vazia"):
        PaginatedClient(provider).fetch_all()


def test_missing_cursor_field_is_a_contract_error() -> None:
    provider = ScriptedProvider({None: {"items": [raw_comment(1)]}})

    with pytest.raises(ContractError, match="next_cursor: campo obrigatório ausente"):
        PaginatedClient(provider).fetch_all()


def test_repeated_cursor_stops_the_walk() -> None:
    provider = ScriptedProvider(
        {
            None: {"items": [raw_comment(2)], "next_cursor": "same"},
            "same": {"items": [raw_comment(1)], "next_cursor": "same"},
        }
    )

    with pytest.raises(CursorLoopError, match="cursor repetido"):
        PaginatedClient(provider).fetch_all()

    assert provider.calls == [None, "same"]


def test_duplicate_item_between_pages_is_rejected() -> None:
    provider = ScriptedProvider(
        {
            None: {"items": [raw_comment(2)], "next_cursor": "p2"},
            "p2": {"items": [raw_comment(2)], "next_cursor": None},
        }
    )

    with pytest.raises(ContractError, match="item duplicado entre páginas: 2"):
        PaginatedClient(provider).fetch_all()
