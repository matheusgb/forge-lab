from collections.abc import Callable
from typing import Protocol

from paginated_contract.contract import parse_page
from paginated_contract.errors import ContractError, CursorLoopError
from paginated_contract.model import Comment, OffsetPage, WalkResult

AfterPage = Callable[[int], None]


class CursorTransport(Protocol):
    def get_page(self, cursor: str | None) -> object: ...


class OffsetTransport(Protocol):
    def get_offset_page(self, offset: int) -> OffsetPage: ...


class PaginatedClient:
    def __init__(self, transport: CursorTransport, max_pages: int = 100) -> None:
        if max_pages <= 0:
            raise ValueError("max_pages precisa ser positivo")
        self._transport = transport
        self._max_pages = max_pages

    def fetch_all(self, after_page: AfterPage | None = None) -> WalkResult:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        seen_items: set[int] = set()
        items: list[Comment] = []
        pages: list[tuple[int, ...]] = []

        for page_number in range(1, self._max_pages + 1):
            if cursor is not None:
                if cursor in seen_cursors:
                    raise CursorLoopError(f"cursor repetido: {cursor}")
                seen_cursors.add(cursor)

            page = parse_page(self._transport.get_page(cursor))
            page_ids = tuple(item.id for item in page.items)
            duplicate_ids = seen_items.intersection(page_ids)
            if duplicate_ids:
                duplicate = min(duplicate_ids)
                raise ContractError(f"item duplicado entre páginas: {duplicate}")

            seen_items.update(page_ids)
            items.extend(page.items)
            pages.append(page_ids)
            if after_page is not None:
                after_page(page_number)

            if page.next_cursor is None:
                return WalkResult(items=tuple(items), pages=tuple(pages))
            cursor = page.next_cursor

        raise ContractError(f"limite de {self._max_pages} páginas excedido")


class OffsetPaginatedClient:
    def __init__(self, transport: OffsetTransport, max_pages: int = 100) -> None:
        if max_pages <= 0:
            raise ValueError("max_pages precisa ser positivo")
        self._transport = transport
        self._max_pages = max_pages

    def fetch_all(self, after_page: AfterPage | None = None) -> WalkResult:
        offset = 0
        items: list[Comment] = []
        pages: list[tuple[int, ...]] = []

        for page_number in range(1, self._max_pages + 1):
            page = self._transport.get_offset_page(offset)
            items.extend(page.items)
            pages.append(tuple(item.id for item in page.items))
            if after_page is not None:
                after_page(page_number)

            if page.next_offset is None:
                return WalkResult(items=tuple(items), pages=tuple(pages))
            offset = page.next_offset

        raise ContractError(f"limite de {self._max_pages} páginas excedido")
