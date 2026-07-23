from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EventKind(StrEnum):
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"


class InboxStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class CrashPoint(StrEnum):
    BEFORE_EFFECT = "before_effect"
    AFTER_EFFECT = "after_effect"


class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    event_id: NonEmptyText
    kind: EventKind = Field(alias="type")
    order_id: NonEmptyText
    occurred_at: AwareDatetime


@dataclass(frozen=True)
class InboxRecord:
    event: WebhookEvent
    raw_body: bytes
    received_at: datetime
    status: InboxStatus = InboxStatus.RECEIVED
    failure_reason: str | None = None


@dataclass(frozen=True)
class ReceiveResult:
    record: InboxRecord
    created: bool


@dataclass(frozen=True)
class Effect:
    event_id: str
    kind: EventKind
    order_id: str
