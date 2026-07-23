import asyncio
from contextlib import suppress

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractIncomingMessage, AbstractQueue

from broker_models.model import Event, RabbitDelivery, RabbitRun, Scenario


async def run_rabbit(scenario: Scenario) -> RabbitRun:
    connection = await aio_pika.connect_robust(scenario.rabbit_url)
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=scenario.rabbit_prefetch)
        exchange = await channel.declare_exchange(
            scenario.rabbit_exchange,
            ExchangeType.DIRECT,
            durable=False,
        )
        queue = await channel.declare_queue(scenario.rabbit_queue, durable=False)
        await queue.bind(exchange, routing_key=scenario.rabbit_routing_key)
        alternate_queue = await channel.declare_queue(
            scenario.rabbit_alternate_queue,
            durable=False,
        )
        await alternate_queue.bind(
            exchange,
            routing_key=scenario.rabbit_alternate_routing_key,
        )
        await queue.purge()
        await alternate_queue.purge()

        for event in scenario.events:
            await exchange.publish(
                Message(
                    body=event.to_bytes(),
                    content_type="application/json",
                    delivery_mode=DeliveryMode.NOT_PERSISTENT,
                ),
                routing_key=scenario.rabbit_routing_key,
            )

        routing_probe = Event(
            event_id="evt-routing-probe",
            order_id="routing-probe",
            sequence=1,
        )
        await exchange.publish(
            Message(body=routing_probe.to_bytes(), content_type="application/json"),
            routing_key=scenario.rabbit_alternate_routing_key,
        )
        alternate_message = await alternate_queue.get(timeout=scenario.timeout_seconds)
        alternate_delivery = RabbitDelivery(
            event=Event.from_bytes(alternate_message.body),
            delivery_tag=alternate_message.delivery_tag or 0,
            redelivered=bool(alternate_message.redelivered),
            decision="ack",
        )
        await alternate_message.ack()

        deliveries, deliveries_while_blocked = await _consume_main_queue(queue, scenario)
    finally:
        await connection.close()
    return RabbitRun(
        deliveries=deliveries,
        alternate_delivery=alternate_delivery,
        deliveries_started_while_first_unacked=deliveries_while_blocked,
        prefetch=scenario.rabbit_prefetch,
        main_routing_key=scenario.rabbit_routing_key,
        alternate_routing_key=scenario.rabbit_alternate_routing_key,
    )


async def _consume_main_queue(
    queue: AbstractQueue,
    scenario: Scenario,
) -> tuple[tuple[RabbitDelivery, ...], int]:
    deliveries: list[RabbitDelivery] = []
    acknowledged: set[str] = set()
    rejected_event_id: str | None = None
    attempts_started = 0
    first_started = asyncio.Event()
    second_started = asyncio.Event()
    release_first = asyncio.Event()
    all_acknowledged = asyncio.Event()

    async def handle(message: AbstractIncomingMessage) -> None:
        nonlocal attempts_started, rejected_event_id
        attempts_started += 1
        if attempts_started == 2:
            second_started.set()

        event = Event.from_bytes(message.body)
        if rejected_event_id is None:
            rejected_event_id = event.event_id
            first_started.set()
            await release_first.wait()
            decision = "nack-requeue"
            await message.nack(requeue=True)
        else:
            decision = "ack"
            acknowledged.add(event.event_id)
            await message.ack()

        deliveries.append(
            RabbitDelivery(
                event=event,
                delivery_tag=message.delivery_tag or 0,
                redelivered=bool(message.redelivered),
                decision=decision,
            )
        )
        if len(acknowledged) == len(scenario.events):
            all_acknowledged.set()

    consumer_tag = await queue.consume(handle)
    try:
        await asyncio.wait_for(first_started.wait(), timeout=scenario.timeout_seconds)
        with suppress(TimeoutError):
            await asyncio.wait_for(second_started.wait(), timeout=0.25)
        deliveries_while_blocked = attempts_started
        release_first.set()
        await asyncio.wait_for(all_acknowledged.wait(), timeout=scenario.timeout_seconds)
    finally:
        release_first.set()
        await queue.cancel(consumer_tag)

    return tuple(deliveries), deliveries_while_blocked
