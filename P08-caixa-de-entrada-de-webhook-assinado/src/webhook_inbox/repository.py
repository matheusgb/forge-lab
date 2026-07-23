from dataclasses import replace
from datetime import datetime

from webhook_inbox.errors import DuplicateEventConflictError, EventNotFoundError
from webhook_inbox.model import InboxRecord, InboxStatus, ReceiveResult, WebhookEvent


class InMemoryInbox:
    def __init__(self) -> None:
        self._records: dict[str, InboxRecord] = {}

    def save_received(
        self,
        event: WebhookEvent,
        raw_body: bytes,
        received_at: datetime,
    ) -> ReceiveResult:
        existing = self._records.get(event.event_id)
        if existing is not None:
            if existing.raw_body != raw_body:
                raise DuplicateEventConflictError(
                    f"event_id {event.event_id} já existe com outro conteúdo"
                )
            return ReceiveResult(record=existing, created=False)

        record = InboxRecord(event=event, raw_body=raw_body, received_at=received_at)
        self._records[event.event_id] = record
        return ReceiveResult(record=record, created=True)

    def get(self, event_id: str) -> InboxRecord:
        record = self._records.get(event_id)
        if record is None:
            raise EventNotFoundError(f"evento não encontrado: {event_id}")
        return record

    def mark_processed(self, event_id: str) -> InboxRecord:
        record = replace(
            self.get(event_id),
            status=InboxStatus.PROCESSED,
            failure_reason=None,
        )
        self._records[event_id] = record
        return record

    def mark_failed(self, event_id: str, reason: str) -> InboxRecord:
        record = replace(
            self.get(event_id),
            status=InboxStatus.FAILED,
            failure_reason=reason,
        )
        self._records[event_id] = record
        return record

    def received(self) -> tuple[InboxRecord, ...]:
        return tuple(
            record for record in self._records.values() if record.status is InboxStatus.RECEIVED
        )

    def all(self) -> tuple[InboxRecord, ...]:
        return tuple(self._records.values())
