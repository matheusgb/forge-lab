from datetime import UTC, datetime

import pytest

from paginated_contract.client import PaginatedClient
from paginated_contract.errors import InvalidCursorError
from paginated_contract.feed import MutableCommentFeed
from paginated_contract.model import Comment


def make_comment(comment_id: int) -> Comment:
    return Comment(
        id=comment_id,
        body=f"Comentário {comment_id}",
        created_at=datetime(2026, 7, 22, 12, comment_id, tzinfo=UTC),
    )


def build_feed(*, insert_new_comment: bool = False) -> MutableCommentFeed:
    feed = MutableCommentFeed(
        comments=tuple(make_comment(comment_id) for comment_id in range(6, 0, -1)),
        page_size=2,
    )
    if insert_new_comment:
        feed.schedule_insert(after_page=1, comment=make_comment(7))
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


def test_offset_drifts_when_a_comment_is_inserted_at_the_top() -> None:
    pages = walk_offset(build_feed(insert_new_comment=True))

    assert pages == ((6, 5), (5, 4), (3, 2), (1,))


def test_snapshot_cursor_keeps_the_original_reading_window() -> None:
    feed = build_feed(insert_new_comment=True)

    result = PaginatedClient(feed).fetch_all()

    assert result.pages == ((6, 5), (4, 3), (2, 1))
    assert result.ids == (6, 5, 4, 3, 2, 1)
    assert PaginatedClient(feed).fetch_all().pages[0] == (7, 6)


def test_provider_rejects_an_invalid_cursor() -> None:
    with pytest.raises(InvalidCursorError, match="cursor inválido"):
        build_feed().get_page("não-é-base64")
