from collections import defaultdict

from broker_models.model import ExperimentResult, KafkaDelivery


def key_sequences(deliveries: tuple[KafkaDelivery, ...]) -> dict[str, tuple[int, ...]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for delivery in deliveries:
        grouped[delivery.event.order_id].append(delivery.event.sequence)
    return {key: tuple(sequences) for key, sequences in grouped.items()}


def same_events(
    first: tuple[KafkaDelivery, ...],
    second: tuple[KafkaDelivery, ...],
) -> bool:
    return {item.event.event_id for item in first} == {item.event.event_id for item in second}


def same_key_order_is_preserved(
    produced: tuple[KafkaDelivery, ...],
    consumed: tuple[KafkaDelivery, ...],
) -> bool:
    if not same_events(produced, consumed):
        return False
    if key_sequences(produced) != key_sequences(consumed):
        return False

    produced_partitions = {item.event.event_id: item.partition for item in produced}
    for order_id in key_sequences(consumed):
        deliveries = [item for item in consumed if item.event.order_id == order_id]
        partitions = {item.partition for item in deliveries}
        offsets = tuple(item.offset for item in deliveries)
        if len(partitions) != 1 or offsets != tuple(sorted(set(offsets))):
            return False
        if any(produced_partitions[item.event.event_id] != item.partition for item in deliveries):
            return False
    return True


def render_report(result: ExperimentResult) -> str:
    kafka_lines = [
        (
            f"  {item.event.event_id}: key={item.event.order_id}; "
            f"partition={item.partition}; offset={item.offset}"
        )
        for item in result.kafka_produced
    ]
    rabbit_lines = [
        (
            f"  {item.event.event_id}: tag={item.delivery_tag}; "
            f"redelivered={item.redelivered}; decisão={item.decision}"
        )
        for item in result.rabbit.deliveries
    ]
    replayed_ids = tuple(item.event.event_id for item in result.kafka_replayed)
    redeliveries = sum(item.redelivered for item in result.rabbit.deliveries)
    main_ids = tuple(dict.fromkeys(item.event.event_id for item in result.rabbit.deliveries))

    return "\n".join(
        [
            "Kafka, modelo de log:",
            *kafka_lines,
            (
                "  ordem publicada por chave preservada="
                f"{same_key_order_is_preserved(result.kafka_produced, result.kafka_consumed)}"
            ),
            f"  replay por novo group={replayed_ids}",
            f"  replay completo={same_events(result.kafka_produced, result.kafka_replayed)}",
            f"  mesmo group retomou no fim={result.kafka_live_group_resumed_at_end}",
            "  ordem global entre partições não é garantida",
            "RabbitMQ, modelo de fila:",
            *rabbit_lines,
            (
                f"  routing {result.rabbit.main_routing_key} -> eventos {main_ids}; "
                f"routing {result.rabbit.alternate_routing_key} -> "
                f"{result.rabbit.alternate_delivery.event.event_id}"
            ),
            (
                f"  prefetch={result.rabbit.prefetch}; entregas iniciadas enquanto a primeira "
                f"estava sem ack={result.rabbit.deliveries_started_while_first_unacked}"
            ),
            f"  redeliveries={redeliveries}",
            "Conclusão:",
            "  Kafka mantém posição por partição e permite outra leitura pelo offset.",
            "  RabbitMQ mantém a mensagem pendente até ack e redelivera depois de nack.",
        ]
    )
