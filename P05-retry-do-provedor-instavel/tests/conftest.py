from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest

from retry_client.client import RetryingProviderClient, TimeoutSettings
from retry_client.model import RetryPolicy
from retry_client.provider import FakeProvider, Outcome
from retry_client.timing import FixedClock, FixedRandom, RecordingWait

ClientBuilder = Callable[
    [tuple[Outcome, ...]],
    tuple[RetryingProviderClient, FakeProvider, RecordingWait],
]


@pytest.fixture
def policy() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=3,
        base_delay_seconds=0.5,
        max_delay_seconds=5,
        jitter_ratio=0.2,
    )


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 7, 21, 12, tzinfo=UTC))


def build_client(
    outcomes: tuple[Outcome, ...],
    policy: RetryPolicy,
    fixed_clock: FixedClock,
) -> tuple[RetryingProviderClient, FakeProvider, RecordingWait]:
    provider = FakeProvider(outcomes)
    wait = RecordingWait()
    client = RetryingProviderClient(
        transport=provider.transport(),
        policy=policy,
        timeout=TimeoutSettings(),
        clock=fixed_clock,
        wait=wait,
        random_value=FixedRandom(0.5),
    )
    return client, provider, wait


@pytest.fixture
def client_builder(
    policy: RetryPolicy,
    fixed_clock: FixedClock,
) -> Iterator[ClientBuilder]:
    clients: list[RetryingProviderClient] = []

    def build(
        outcomes: tuple[Outcome, ...],
    ) -> tuple[RetryingProviderClient, FakeProvider, RecordingWait]:
        client, provider, wait = build_client(outcomes, policy, fixed_clock)
        clients.append(client)
        return client, provider, wait

    yield build
    for client in clients:
        client.http.close()
