import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

from order_normalizer.errors import (
    InvalidDateError,
    InvalidFieldError,
    InvalidJsonError,
    MissingFieldError,
    NormalizationError,
    UnknownCurrencyError,
)
from order_normalizer.models import Currency, Money, Order, Result


def _required(record: dict[str, object], field: str, line_number: int) -> object:
    try:
        return record[field]
    except KeyError as error:
        raise MissingFieldError(field, line_number=line_number) from error


def _required_text(record: dict[str, object], field: str, line_number: int) -> str:
    value = _required(record, field, line_number)
    if not isinstance(value, str) or not value.strip():
        raise InvalidFieldError(
            field, f"{field} must be a non-empty string", line_number=line_number
        )
    return value.strip()


def _parse_currency(value: str, line_number: int) -> Currency:
    normalized = value.upper()
    try:
        return Currency(normalized)
    except ValueError as error:
        raise UnknownCurrencyError(normalized, line_number=line_number) from error


def _parse_amount(value: object, line_number: int) -> Decimal:
    if not isinstance(value, (int, float, str)) or isinstance(value, bool):
        raise InvalidFieldError("amount", "amount must be numeric", line_number=line_number)
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation as error:
        raise InvalidFieldError(
            "amount", "amount must be numeric", line_number=line_number
        ) from error
    if amount <= 0:
        raise InvalidFieldError("amount", "amount must be positive", line_number=line_number)
    return amount


def _parse_date(value: str, line_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone is required")
        return parsed.astimezone(UTC)
    except ValueError as error:
        raise InvalidDateError(value, line_number=line_number) from error


def _parse_tags(value: object, line_number: int) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise InvalidFieldError("tags", "tags must be a list of strings", line_number=line_number)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in cast(list[object], value):
        if not isinstance(item, str) or not item.strip():
            raise InvalidFieldError(
                "tags", "tags must be a list of strings", line_number=line_number
            )
        tag = item.strip().lower()
        if tag not in seen:
            seen.add(tag)
            normalized.append(tag)
    return tuple(normalized)


def _parse_note(value: object, line_number: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidFieldError("note", "note must be a string or null", line_number=line_number)
    normalized = value.strip()
    return normalized or None


def _decode(line: str, line_number: int) -> dict[str, object]:
    try:
        decoded = cast(object, json.loads(line))
    except json.JSONDecodeError as error:
        raise InvalidJsonError(line_number=line_number) from error
    if not isinstance(decoded, dict):
        raise InvalidFieldError("root", "JSON line must be an object", line_number=line_number)
    return cast(dict[str, object], decoded)


def normalize_line(line: str, line_number: int) -> Result[Order]:
    try:
        record = _decode(line, line_number)
        order_id = _required_text(record, "order_id", line_number)
        created_at = _parse_date(_required_text(record, "created_at", line_number), line_number)
        currency = _parse_currency(_required_text(record, "currency", line_number), line_number)
        amount = _parse_amount(_required(record, "amount", line_number), line_number)
        tags = _parse_tags(record.get("tags"), line_number)
        note = _parse_note(record.get("note"), line_number)
        return Result[Order](value=Order(order_id, created_at, Money(amount, currency), tags, note))
    except NormalizationError as error:
        return Result[Order](error=error)
