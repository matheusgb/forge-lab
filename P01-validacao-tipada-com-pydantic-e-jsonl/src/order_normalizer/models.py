from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator

from order_normalizer.errors import ErrorCode

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Currency(StrEnum):
    BRL = "BRL"
    EUR = "EUR"
    USD = "USD"


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    order_id: NonEmptyText
    created_at: AwareDatetime
    amount: Decimal = Field(gt=0)
    currency: Currency
    tags: tuple[NonEmptyText, ...] = ()
    note: str | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("created_at")
    @classmethod
    def normalize_date(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tag.lower() for tag in tags))

    @field_validator("note")
    @classmethod
    def normalize_note(cls, note: str | None) -> str | None:
        return note or None


class RejectedRecord(BaseModel):
    line: int
    code: ErrorCode
    field: str | None
    message: str
    raw: str
