from pathlib import Path

import pytest
from pydantic import ValidationError

from broker_models.model import Event, Scenario

PROJECT = Path(__file__).resolve().parents[1]


def test_scenario_loads_the_fixed_events() -> None:
    scenario = Scenario.load(PROJECT / "scenario.yaml")

    assert len(scenario.events) == 6
    assert scenario.rabbit_prefetch == 1
    assert scenario.rabbit_routing_key != scenario.rabbit_alternate_routing_key


def test_scenario_rejects_duplicate_event_ids() -> None:
    data = Scenario.load(PROJECT / "scenario.yaml").model_dump(mode="json")
    data["events"][1]["event_id"] = data["events"][0]["event_id"]

    with pytest.raises(ValidationError, match="event_id duplicado"):
        Scenario.model_validate(data)


def test_event_round_trip_preserves_the_contract() -> None:
    event = Event(event_id="evt-1", order_id="order-1", sequence=1)

    assert Event.from_bytes(event.to_bytes()) == event
