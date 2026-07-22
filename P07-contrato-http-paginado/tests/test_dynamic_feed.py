import pytest

from paginated_contract.client import OffsetPaginatedClient, PaginatedClient
from paginated_contract.errors import InvalidCursorError
from paginated_contract.feed import MutableCommentFeed
from paginated_contract.model import Comment


def make_comment(comment_id: int) -> Comment:
    return Comment(
        id=comment_id,
        body=f"Comentário {comment_id}",
        created_at=f"2026-07-22T12:{comment_id:02d}:00Z",
    )


def build_feed() -> MutableCommentFeed:
    return MutableCommentFeed(
        comments=tuple(make_comment(comment_id) for comment_id in range(6, 0, -1)),
        page_size=2,
    )


def insert_after_first_page(feed: MutableCommentFeed, page_number: int) -> None:
    if page_number == 1:
        feed.add_comment(make_comment(7))


def test_offset_drifts_when_a_comment_is_inserted_at_the_top() -> None:
    feed = build_feed()

    result = OffsetPaginatedClient(feed).fetch_all(
        after_page=lambda page: insert_after_first_page(feed, page)
    )

    assert result.pages == ((6, 5), (5, 4), (3, 2), (1,))
    assert result.ids.count(5) == 2


def test_snapshot_cursor_keeps_the_original_reading_window() -> None:
    feed = build_feed()

    result = PaginatedClient(feed).fetch_all(
        after_page=lambda page: insert_after_first_page(feed, page)
    )

    assert result.pages == ((6, 5), (4, 3), (2, 1))
    assert result.ids == (6, 5, 4, 3, 2, 1)

    refreshed = PaginatedClient(feed).fetch_all()
    assert refreshed.pages[0] == (7, 6)


def test_provider_rejects_an_invalid_cursor() -> None:
    feed = build_feed()

    with pytest.raises(InvalidCursorError, match="cursor inválido"):
        feed.get_page("não-é-base64")
