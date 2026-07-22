from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Mapping
from dataclasses import dataclass

from paginated_contract.errors import InvalidCursorError
from paginated_contract.model import Comment, OffsetPage


@dataclass(frozen=True)
class CursorState:
    snapshot_id: int
    after_id: int


class ScriptedProvider:
    def __init__(self, pages: Mapping[str | None, object]) -> None:
        self._pages = dict(pages)
        self.calls: list[str | None] = []

    def get_page(self, cursor: str | None) -> object:
        self.calls.append(cursor)
        if cursor not in self._pages:
            raise InvalidCursorError(f"cursor desconhecido: {cursor!r}")
        return self._pages[cursor]


def _encode_cursor(state: CursorState) -> str:
    payload = f"{state.snapshot_id}:{state.after_id}".encode()
    return urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> CursorState:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = urlsafe_b64decode(f"{cursor}{padding}").decode()
        snapshot_text, after_text = decoded.split(":", maxsplit=1)
        state = CursorState(snapshot_id=int(snapshot_text), after_id=int(after_text))
    except (UnicodeDecodeError, ValueError) as error:
        raise InvalidCursorError("cursor inválido") from error

    if state.snapshot_id < 0 or state.after_id < 0 or state.after_id > state.snapshot_id:
        raise InvalidCursorError("cursor contém uma posição impossível")
    return state


class MutableCommentFeed:
    def __init__(self, comments: tuple[Comment, ...], page_size: int) -> None:
        if page_size <= 0:
            raise ValueError("page_size precisa ser positivo")
        self._comments = list(comments)
        self._page_size = page_size
        self._sort()

    def _sort(self) -> None:
        self._comments.sort(key=lambda comment: comment.id, reverse=True)

    def add_comment(self, comment: Comment) -> None:
        if any(existing.id == comment.id for existing in self._comments):
            raise ValueError(f"comentário duplicado: {comment.id}")
        self._comments.append(comment)
        self._sort()

    def get_offset_page(self, offset: int) -> OffsetPage:
        if offset < 0:
            raise ValueError("offset não pode ser negativo")
        items = tuple(self._comments[offset : offset + self._page_size])
        consumed = offset + len(items)
        next_offset = consumed if consumed < len(self._comments) else None
        return OffsetPage(items=items, next_offset=next_offset)

    def get_page(self, cursor: str | None) -> object:
        if cursor is None:
            snapshot_id = self._comments[0].id if self._comments else 0
            after_id: int | None = None
        else:
            state = _decode_cursor(cursor)
            snapshot_id = state.snapshot_id
            after_id = state.after_id

        eligible = [
            comment
            for comment in self._comments
            if comment.id <= snapshot_id and (after_id is None or comment.id < after_id)
        ]
        items = eligible[: self._page_size]
        has_more = len(eligible) > len(items)
        next_cursor = (
            _encode_cursor(CursorState(snapshot_id=snapshot_id, after_id=items[-1].id))
            if has_more and items
            else None
        )
        return {
            "items": [
                {
                    "id": item.id,
                    "body": item.body,
                    "created_at": item.created_at,
                }
                for item in items
            ],
            "next_cursor": next_cursor,
        }
