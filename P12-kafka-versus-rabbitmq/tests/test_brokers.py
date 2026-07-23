import asyncio
import os
from pathlib import Path

import pytest

from broker_models.comparison import same_events, same_key_order_is_preserved
from broker_models.experiment import run_experiment

PROJECT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_BROKER_TESTS") != "1",
    reason="defina RUN_BROKER_TESTS=1 com os brokers ativos",
)
def test_real_brokers_expose_their_different_delivery_models() -> None:
    result = asyncio.run(run_experiment(PROJECT, write_evidence=False))

    assert same_key_order_is_preserved(result.kafka_produced, result.kafka_consumed)
    assert same_key_order_is_preserved(result.kafka_produced, result.kafka_replayed)
    assert same_events(result.kafka_produced, result.kafka_replayed)
    assert result.kafka_live_group_resumed_at_end

    nacked = next(item for item in result.rabbit.deliveries if item.decision == "nack-requeue")
    assert any(
        item.event.event_id == nacked.event.event_id and item.decision == "ack" and item.redelivered
        for item in result.rabbit.deliveries
    )
    assert result.rabbit.deliveries_started_while_first_unacked == 1
    assert {item.event.event_id for item in result.rabbit.deliveries} == {
        item.event.event_id for item in result.kafka_produced
    }
    assert result.rabbit.alternate_delivery.event.event_id == "evt-routing-probe"
