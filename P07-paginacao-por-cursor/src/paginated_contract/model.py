from dataclasses import dataclass
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, model_validator

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: int
    body: NonEmptyText
    created_at: AwareDatetime


class Page(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    items: tuple[Comment, ...]
    next_cursor: NonEmptyText | None

    @model_validator(mode="after")
    def terminal_empty_page(self) -> Self:
        if not self.items and self.next_cursor is not None:
            raise ValueError("página vazia não pode apontar para outra página")
        return self


@dataclass(frozen=True)
class WalkResult:
    items: tuple[Comment, ...]
    pages: tuple[tuple[int, ...], ...]

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(item.id for item in self.items)
