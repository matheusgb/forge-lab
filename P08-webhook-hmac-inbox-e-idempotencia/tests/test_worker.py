import pytest

from tests.conftest import signed_headers
from webhook_inbox.api import AppContainer
from webhook_inbox.errors import SimulatedCrash
from webhook_inbox.model import CrashPoint, EventKind, InboxStatus


def deliver(
    container: AppContainer,
    body: bytes,
) -> bool:
    headers = signed_headers(body)
    result = container.receiver.receive(
        raw_body=body,
        timestamp_header=headers["X-Webhook-Timestamp"],
        signature_header=headers["X-Webhook-Signature"],
    )
    return result.created


def test_three_deliveries_produce_one_effect(
    container: AppContainer,
    authorized_body: bytes,
) -> None:
    deliveries = [deliver(container, authorized_body) for _ in range(3)]

    record = container.worker.process("evt-authorized-1")

    assert deliveries == [True, False, False]
    assert record.status is InboxStatus.PROCESSED
    assert len(container.inbox.all()) == 1
    assert [effect.event_id for effect in container.effects.effects] == ["evt-authorized-1"]


def test_crash_before_effect_leaves_received_event_for_recovery(
    container: AppContainer,
    authorized_body: bytes,
) -> None:
    deliver(container, authorized_body)

    with pytest.raises(SimulatedCrash, match="antes do efeito"):
        container.worker.process("evt-authorized-1", crash_at=CrashPoint.BEFORE_EFFECT)

    assert container.inbox.get("evt-authorized-1").status is InboxStatus.RECEIVED
    assert container.effects.effects == ()

    recovered = container.worker.process("evt-authorized-1")
    assert recovered.status is InboxStatus.PROCESSED
    assert len(container.effects.effects) == 1


def test_crash_after_effect_does_not_duplicate_effect_on_recovery(
    container: AppContainer,
    authorized_body: bytes,
) -> None:
    deliver(container, authorized_body)

    with pytest.raises(SimulatedCrash, match="depois do efeito"):
        container.worker.process("evt-authorized-1", crash_at=CrashPoint.AFTER_EFFECT)

    assert container.inbox.get("evt-authorized-1").status is InboxStatus.RECEIVED
    assert len(container.effects.effects) == 1

    recovered = container.worker.process("evt-authorized-1")
    assert recovered.status is InboxStatus.PROCESSED
    assert len(container.effects.effects) == 1


def test_captured_before_authorized_is_stored_as_failed(
    container: AppContainer,
) -> None:
    body = (
        b'{"event_id":"evt-captured-early","occurred_at":"2026-07-22T14:59:40Z",'
        b'"order_id":"order-2","type":"payment.captured"}'
    )
    deliver(container, body)

    record = container.worker.process("evt-captured-early")

    assert record.status is InboxStatus.FAILED
    assert record.failure_reason is not None
    assert "exige payment.authorized" in record.failure_reason
    assert container.effects.effects == ()


def test_authorized_then_captured_produce_two_ordered_effects(
    container: AppContainer,
    authorized_body: bytes,
) -> None:
    captured_body = (
        b'{"event_id":"evt-captured-1","occurred_at":"2026-07-22T14:59:40Z",'
        b'"order_id":"order-1","type":"payment.captured"}'
    )
    deliver(container, authorized_body)
    deliver(container, captured_body)

    authorized = container.worker.process("evt-authorized-1")
    captured = container.worker.process("evt-captured-1")

    assert authorized.status is InboxStatus.PROCESSED
    assert captured.status is InboxStatus.PROCESSED
    assert [effect.kind for effect in container.effects.effects] == [
        EventKind.PAYMENT_AUTHORIZED,
        EventKind.PAYMENT_CAPTURED,
    ]
