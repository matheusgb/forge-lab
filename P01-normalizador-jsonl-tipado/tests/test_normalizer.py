from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from order_normalizer.errors import ErrorCode, RejectedLine
from order_normalizer.models import Currency
from order_normalizer.normalizer import normalize_line


def test_normalizes_order() -> None:
    order = normalize_line(
        '{"order_id":"o-1","created_at":"2026-07-20T10:00:00-03:00",'
        '"amount":"12.345","currency":"brl","tags":["VIP","vip"],"note":"  ok "}',
        1,
    )

    assert order.created_at == datetime(2026, 7, 20, 13, tzinfo=UTC)
    assert order.amount == Decimal("12.34")
    assert order.currency is Currency.BRL
    assert order.tags == ("vip",)
    assert order.note == "ok"


@pytest.mark.parametrize(
    ("line", "code"),
    [
        ('{"order_id":', ErrorCode.INVALID_JSON),
        (
            '{"created_at":"2026-07-20T10:00:00Z","amount":1,"currency":"BRL"}',
            ErrorCode.MISSING_FIELD,
        ),
        (
            '{"order_id":"o","created_at":"2026-07-20T10:00:00Z","amount":1,"currency":"JPY"}',
            ErrorCode.UNKNOWN_CURRENCY,
        ),
        (
            '{"order_id":"o","created_at":"amanhã","amount":1,"currency":"BRL"}',
            ErrorCode.INVALID_DATE,
        ),
    ],
)
def test_classifies_domain_errors_and_preserves_cause(line: str, code: ErrorCode) -> None:
    with pytest.raises(RejectedLine) as captured:
        normalize_line(line, 7)

    assert captured.value.code is code
    assert captured.value.line_number == 7
    assert isinstance(captured.value.__cause__, ValidationError)
