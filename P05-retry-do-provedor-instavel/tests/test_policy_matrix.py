from collections.abc import Callable

import pytest

from retry_client.client import RetryingProviderClient
from retry_client.model import Decision, Operation
from retry_client.provider import FakeProvider, Outcome
from retry_client.timing import RecordingWait

ClientBuilder = Callable[
    [tuple[Outcome, ...]],
    tuple[RetryingProviderClient, FakeProvider, RecordingWait],
]


@pytest.mark.parametrize(
    ("operation", "outcome", "expected"),
    [
        (Operation.SAFE_READ, Outcome.response(200), Decision.SUCCESS),
        (Operation.SAFE_READ, Outcome.response(400), Decision.STOP_PERMANENT),
        (Operation.UNSAFE_CREATE, Outcome.response(400), Decision.STOP_PERMANENT),
        (Operation.UNSAFE_CREATE, Outcome.response(429), Decision.STOP_UNSAFE),
        (Operation.UNSAFE_CREATE, Outcome.response(500), Decision.STOP_UNSAFE),
        (Operation.UNSAFE_CREATE, Outcome.timeout(), Decision.STOP_UNSAFE),
    ],
)
def test_terminal_decision_matrix(
    client_builder: ClientBuilder,
    operation: Operation,
    outcome: Outcome,
    expected: Decision,
) -> None:
    client, _, _ = client_builder((outcome,))

    report = client.call(operation)

    assert report.final_decision is expected


@pytest.mark.parametrize(
    "outcome",
    [Outcome.response(429), Outcome.response(500), Outcome.timeout()],
)
def test_safe_transient_failure_stops_after_budget(
    client_builder: ClientBuilder,
    outcome: Outcome,
) -> None:
    client, provider, wait = client_builder((outcome, outcome, outcome))

    report = client.call(Operation.SAFE_READ)

    assert provider.attempts == 3
    assert len(wait.calls) == 2
    assert report.final_decision is Decision.STOP_EXHAUSTED
