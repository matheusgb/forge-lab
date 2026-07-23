from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    StringConstraints,
    model_validator,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: NonEmptyText
    order_id: NonEmptyText
    sequence: PositiveInt

    def to_bytes(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def from_bytes(cls, payload: bytes) -> Self:
        return cls.model_validate_json(payload)


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: NonEmptyText
    kafka_bootstrap_servers: NonEmptyText
    kafka_topic: NonEmptyText
    kafka_live_group: NonEmptyText
    kafka_replay_group: NonEmptyText
    rabbit_url: NonEmptyText
    rabbit_exchange: NonEmptyText
    rabbit_queue: NonEmptyText
    rabbit_routing_key: NonEmptyText
    rabbit_alternate_queue: NonEmptyText
    rabbit_alternate_routing_key: NonEmptyText
    rabbit_prefetch: PositiveInt
    timeout_seconds: PositiveFloat
    events: tuple[Event, ...]

    @model_validator(mode="after")
    def unique_and_ordered_events(self) -> Self:
        if not self.events:
            raise ValueError("o cenário precisa de eventos")
        event_ids = [event.event_id for event in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("event_id duplicado no cenário")
        return self

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class KafkaDelivery(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Event
    partition: NonNegativeInt
    offset: NonNegativeInt


class RabbitDelivery(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Event
    delivery_tag: NonNegativeInt
    redelivered: bool
    decision: Literal["ack", "nack-requeue"]


class RabbitRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    deliveries: tuple[RabbitDelivery, ...]
    alternate_delivery: RabbitDelivery
    deliveries_started_while_first_unacked: PositiveInt
    prefetch: PositiveInt
    main_routing_key: NonEmptyText
    alternate_routing_key: NonEmptyText


class ExperimentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    kafka_topic: NonEmptyText
    kafka_produced: tuple[KafkaDelivery, ...]
    kafka_consumed: tuple[KafkaDelivery, ...]
    kafka_replayed: tuple[KafkaDelivery, ...]
    kafka_live_group_resumed_at_end: bool
    rabbit: RabbitRun
