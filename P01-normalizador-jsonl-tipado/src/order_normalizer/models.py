from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from order_normalizer.errors import NormalizationError


class Currency(StrEnum):
    BRL = "BRL"
    EUR = "EUR"
    USD = "USD"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency


@dataclass(frozen=True)
class Order:
    order_id: str
    created_at: datetime
    total: Money
    tags: tuple[str, ...]
    note: str | None


@dataclass(frozen=True)
class Result[T]:
    value: T | None = None
    error: NormalizationError | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None
