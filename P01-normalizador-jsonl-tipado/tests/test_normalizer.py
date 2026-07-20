from datetime import UTC, datetime
from decimal import Decimal

import pytest

from order_normalizer.errors import ErrorCode
from order_normalizer.models import Currency
from order_normalizer.normalizer import normalize_line


def test_normalizes_order() -> None:
    result = normalize_line(
        '{"order_id":"o-1","created_at":"2026-07-20T10:00:00-03:00",'
        '"amount":"12.345","currency":"brl","tags":["VIP","vip"],"note":"  ok "}',
        1,
    )

    assert result.error is None
    assert result.value is not None
    assert result.value.created_at == datetime(2026, 7, 20, 13, tzinfo=UTC)
    assert result.value.total.amount == Decimal("12.34")
    assert result.value.total.currency is Currency.BRL
    assert result.value.tags == ("vip",)
    assert result.value.note == "ok"


@pytest.mark.parametrize(
    ("line", "code", "cause_type"),
    [
        ('{"order_id":', ErrorCode.INVALID_JSON, "JSONDecodeError"),
        (
            '{"created_at":"2026-07-20T10:00:00Z","amount":1,"currency":"BRL"}',
            ErrorCode.MISSING_FIELD,
            "KeyError",
        ),
        (
            '{"order_id":"o","created_at":"2026-07-20T10:00:00Z","amount":1,"currency":"JPY"}',
            ErrorCode.UNKNOWN_CURRENCY,
            "ValueError",
        ),
        (
            '{"order_id":"o","created_at":"amanhã","amount":1,"currency":"BRL"}',
            ErrorCode.INVALID_DATE,
            "ValueError",
        ),
    ],
)
def test_classifies_domain_errors_and_preserves_cause(
    line: str, code: ErrorCode, cause_type: str
) -> None:
    result = normalize_line(line, 7)

    assert result.value is None
    assert result.error is not None
    assert result.error.code is code
    assert result.error.line_number == 7
    assert result.error.__cause__ is not None
    assert type(result.error.__cause__).__name__ == cause_type
