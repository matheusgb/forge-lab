from typing import Protocol

from paginated_contract.contract import parse_page
from paginated_contract.errors import ContractError, CursorLoopError
from paginated_contract.model import Comment, WalkResult


class PageProvider(Protocol):
    def get_page(self, cursor: str | None) -> object: ...


class PaginatedClient:
    def __init__(self, provider: PageProvider, max_pages: int = 100) -> None:
        if max_pages <= 0:
            raise ValueError("max_pages precisa ser positivo")
        self._provider = provider
        self._max_pages = max_pages

    def fetch_all(self) -> WalkResult:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        seen_items: set[int] = set()
        items: list[Comment] = []
        pages: list[tuple[int, ...]] = []

        for _ in range(self._max_pages):
            if cursor is not None:
                if cursor in seen_cursors:
                    raise CursorLoopError(f"cursor repetido: {cursor}")
                seen_cursors.add(cursor)

            page = parse_page(self._provider.get_page(cursor))
            page_ids = tuple(item.id for item in page.items)
            duplicate_ids = seen_items.intersection(page_ids)
            if duplicate_ids:
                raise ContractError(f"item duplicado entre páginas: {min(duplicate_ids)}")

            seen_items.update(page_ids)
            items.extend(page.items)
            pages.append(page_ids)
            if page.next_cursor is None:
                return WalkResult(items=tuple(items), pages=tuple(pages))
            cursor = page.next_cursor

        raise ContractError(f"limite de {self._max_pages} páginas excedido")
