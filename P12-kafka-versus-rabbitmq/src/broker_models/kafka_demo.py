import asyncio
from collections.abc import Awaitable
from typing import Protocol, cast

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # pyright: ignore[reportMissingTypeStubs]
from aiokafka.admin import (  # pyright: ignore[reportMissingTypeStubs]
    AIOKafkaAdminClient,
    NewTopic,
)

from broker_models.model import Event, KafkaDelivery, Scenario


class _RecordMetadata(Protocol):
    partition: int
    offset: int


class _ConsumerRecord(Protocol):
    value: bytes
    partition: int
    offset: int


class _TopicLister(Protocol):
    def list_topics(self) -> Awaitable[list[str]]: ...


async def _wait_for_topic(
    admin: _TopicLister,
    topic: str,
    *,
    present: bool,
    timeout_seconds: float,
) -> None:
    try:
        async with asyncio.timeout(timeout_seconds):
            while (topic in await admin.list_topics()) is not present:
                await asyncio.sleep(0.05)
    except TimeoutError as error:
        state = "aparecer" if present else "desaparecer"
        raise RuntimeError(f"o tópico {topic} não conseguiu {state}") from error


async def _reset_topic(scenario: Scenario) -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=scenario.kafka_bootstrap_servers)
    await admin.start()
    try:
        topic_lister = cast(_TopicLister, admin)
        if scenario.kafka_topic in await topic_lister.list_topics():
            await admin.delete_topics([scenario.kafka_topic])
            await _wait_for_topic(
                topic_lister,
                scenario.kafka_topic,
                present=False,
                timeout_seconds=scenario.timeout_seconds,
            )
        await admin.create_topics(
            [NewTopic(name=scenario.kafka_topic, num_partitions=3, replication_factor=1)]
        )
        await _wait_for_topic(
            topic_lister,
            scenario.kafka_topic,
            present=True,
            timeout_seconds=scenario.timeout_seconds,
        )
    finally:
        await admin.close()


async def _produce(scenario: Scenario) -> tuple[KafkaDelivery, ...]:
    producer = AIOKafkaProducer(bootstrap_servers=scenario.kafka_bootstrap_servers)
    await producer.start()
    deliveries: list[KafkaDelivery] = []
    try:
        for event in scenario.events:
            metadata = cast(
                _RecordMetadata,
                await producer.send_and_wait(  # pyright: ignore[reportUnknownMemberType]
                    scenario.kafka_topic,
                    key=event.order_id.encode(),
                    value=event.to_bytes(),
                ),
            )
            deliveries.append(
                KafkaDelivery(
                    event=event,
                    partition=metadata.partition,
                    offset=metadata.offset,
                )
            )
    finally:
        await producer.stop()
    return tuple(deliveries)


async def _live_group_resumes_at_end(scenario: Scenario) -> bool:
    consumer = AIOKafkaConsumer(
        scenario.kafka_topic,
        bootstrap_servers=scenario.kafka_bootstrap_servers,
        group_id=scenario.kafka_live_group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    try:
        next_record = cast(
            Awaitable[_ConsumerRecord],
            consumer.getone(),  # pyright: ignore[reportUnknownMemberType]
        )
        try:
            await asyncio.wait_for(next_record, timeout=0.5)
        except TimeoutError:
            return True
        return False
    finally:
        await consumer.stop()


async def _consume(
    scenario: Scenario,
    *,
    group_id: str,
    commit: bool,
) -> tuple[KafkaDelivery, ...]:
    consumer = AIOKafkaConsumer(
        scenario.kafka_topic,
        bootstrap_servers=scenario.kafka_bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    deliveries: list[KafkaDelivery] = []
    try:
        for _ in scenario.events:
            next_record = cast(
                Awaitable[_ConsumerRecord],
                consumer.getone(),  # pyright: ignore[reportUnknownMemberType]
            )
            record = await asyncio.wait_for(
                next_record,
                timeout=scenario.timeout_seconds,
            )
            deliveries.append(
                KafkaDelivery(
                    event=Event.from_bytes(record.value),
                    partition=record.partition,
                    offset=record.offset,
                )
            )
        if commit:
            await consumer.commit()  # pyright: ignore[reportUnknownMemberType]
    finally:
        await consumer.stop()
    return tuple(deliveries)


async def run_kafka(
    scenario: Scenario,
) -> tuple[
    tuple[KafkaDelivery, ...],
    tuple[KafkaDelivery, ...],
    tuple[KafkaDelivery, ...],
    bool,
]:
    await _reset_topic(scenario)
    produced = await _produce(scenario)
    consumed = await _consume(scenario, group_id=scenario.kafka_live_group, commit=True)
    live_group_resumed_at_end = await _live_group_resumes_at_end(scenario)
    replayed = await _consume(scenario, group_id=scenario.kafka_replay_group, commit=False)
    return produced, consumed, replayed, live_group_resumed_at_end
