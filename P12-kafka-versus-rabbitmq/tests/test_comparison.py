from broker_models.comparison import (
    key_sequences,
    render_report,
    same_events,
    same_key_order_is_preserved,
)
from broker_models.model import Event, ExperimentResult, KafkaDelivery, RabbitDelivery, RabbitRun


def kafka_delivery(order_id: str, sequence: int, offset: int) -> KafkaDelivery:
    return KafkaDelivery(
        event=Event(event_id=f"evt-{order_id}-{sequence}", order_id=order_id, sequence=sequence),
        partition=0,
        offset=offset,
    )


def test_order_is_checked_per_key_instead_of_globally() -> None:
    deliveries = (
        kafka_delivery("a", 1, 0),
        kafka_delivery("b", 1, 1),
        kafka_delivery("a", 2, 2),
        kafka_delivery("b", 2, 3),
    )

    assert key_sequences(deliveries) == {"a": (1, 2), "b": (1, 2)}
    consumed = (deliveries[1], deliveries[0], deliveries[3], deliveries[2])

    assert same_key_order_is_preserved(deliveries, consumed)


def test_out_of_order_delivery_for_the_same_key_is_visible() -> None:
    produced = (
        kafka_delivery("a", 1, 0),
        kafka_delivery("a", 2, 1),
    )
    consumed = (
        kafka_delivery("a", 2, 0),
        kafka_delivery("a", 1, 1),
    )

    assert not same_key_order_is_preserved(produced, consumed)


def test_complete_replay_does_not_require_global_order_between_partitions() -> None:
    produced = (kafka_delivery("a", 1, 0), kafka_delivery("b", 1, 0))
    replayed = tuple(reversed(produced))

    assert same_events(produced, replayed)


def test_report_separates_offset_replay_from_ack_redelivery() -> None:
    kafka = (kafka_delivery("a", 1, 0),)
    event = kafka[0].event
    rabbit = (
        RabbitDelivery(
            event=event,
            delivery_tag=1,
            redelivered=False,
            decision="nack-requeue",
        ),
        RabbitDelivery(event=event, delivery_tag=2, redelivered=True, decision="ack"),
    )
    result = ExperimentResult(
        kafka_topic="events",
        kafka_produced=kafka,
        kafka_consumed=kafka,
        kafka_replayed=kafka,
        kafka_live_group_resumed_at_end=True,
        rabbit=RabbitRun(
            deliveries=rabbit,
            alternate_delivery=RabbitDelivery(
                event=Event(event_id="evt-routing", order_id="routing", sequence=1),
                delivery_tag=3,
                redelivered=False,
                decision="ack",
            ),
            deliveries_started_while_first_unacked=1,
            prefetch=1,
            main_routing_key="order.created",
            alternate_routing_key="order.cancelled",
        ),
    )

    report = render_report(result)

    assert "replay por novo group=('evt-a-1',)" in report
    assert "replay completo=True" in report
    assert "mesmo group retomou no fim=True" in report
    assert "redeliveries=1" in report
    assert "Kafka mantém posição por partição" in report
