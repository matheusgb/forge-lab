from dataclasses import dataclass


@dataclass(frozen=True)
class Comment:
    id: int
    body: str
    created_at: str


@dataclass(frozen=True)
class Page:
    items: tuple[Comment, ...]
    next_cursor: str | None


@dataclass(frozen=True)
class OffsetPage:
    items: tuple[Comment, ...]
    next_offset: int | None


@dataclass(frozen=True)
class WalkResult:
    items: tuple[Comment, ...]
    pages: tuple[tuple[int, ...], ...]

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(item.id for item in self.items)
