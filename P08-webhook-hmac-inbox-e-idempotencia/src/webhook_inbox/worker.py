from webhook_inbox.errors import OutOfOrderEventError, SimulatedCrash
from webhook_inbox.model import CrashPoint, Effect, EventKind, InboxRecord, InboxStatus
from webhook_inbox.repository import InMemoryInbox


class InMemoryEffectStore:
    def __init__(self) -> None:
        self._processed_events: set[str] = set()
        self._authorized_orders: set[str] = set()
        self._effects: list[Effect] = []

    def apply_once(self, record: InboxRecord) -> bool:
        event = record.event
        if event.event_id in self._processed_events:
            return False
        if (
            event.kind is EventKind.PAYMENT_CAPTURED
            and event.order_id not in self._authorized_orders
        ):
            raise OutOfOrderEventError(
                f"{event.kind.value} exige payment.authorized para {event.order_id}"
            )

        self._processed_events.add(event.event_id)
        if event.kind is EventKind.PAYMENT_AUTHORIZED:
            self._authorized_orders.add(event.order_id)
        self._effects.append(
            Effect(event_id=event.event_id, kind=event.kind, order_id=event.order_id)
        )
        return True

    @property
    def effects(self) -> tuple[Effect, ...]:
        return tuple(self._effects)


class WebhookWorker:
    def __init__(self, inbox: InMemoryInbox, effects: InMemoryEffectStore) -> None:
        self._inbox = inbox
        self._effects = effects

    def process(self, event_id: str, crash_at: CrashPoint | None = None) -> InboxRecord:
        record = self._inbox.get(event_id)
        if record.status is not InboxStatus.RECEIVED:
            return record

        if crash_at is CrashPoint.BEFORE_EFFECT:
            raise SimulatedCrash("crash depois da persistência e antes do efeito")

        try:
            self._effects.apply_once(record)
        except OutOfOrderEventError as error:
            return self._inbox.mark_failed(event_id, str(error))

        if crash_at is CrashPoint.AFTER_EFFECT:
            raise SimulatedCrash("crash depois do efeito e antes da confirmação")

        return self._inbox.mark_processed(event_id)

    def process_next(self, crash_at: CrashPoint | None = None) -> InboxRecord | None:
        pending = self._inbox.received()
        if not pending:
            return None
        return self.process(pending[0].event.event_id, crash_at=crash_at)
