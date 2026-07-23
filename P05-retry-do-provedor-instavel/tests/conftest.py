from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from httpx2 import Client, Timeout

from retry_client.client import RetryingProviderClient
from retry_client.model import RetryPolicy
from retry_client.provider import FakeProvider, Outcome

ClientBuilder = Callable[
    [tuple[Outcome, ...]],
    tuple[RetryingProviderClient, FakeProvider, list[float]],
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
def fixed_clock() -> datetime:
    return datetime(2026, 7, 21, 12, tzinfo=UTC)


def build_client(
    outcomes: tuple[Outcome, ...],
    policy: RetryPolicy,
    fixed_clock: datetime,
) -> tuple[RetryingProviderClient, FakeProvider, list[float]]:
    provider = FakeProvider(outcomes)
    waits: list[float] = []
    http = Client(
        base_url="https://provider.test",
        transport=provider.transport(),
        timeout=Timeout(connect=0.2, read=0.5, write=0.5, pool=0.2),
    )
    client = RetryingProviderClient(
        http=http,
        policy=policy,
        clock=lambda: fixed_clock,
        wait=waits.append,
        random_value=lambda: 0.5,
    )
    return client, provider, waits


@pytest.fixture
def client_builder(
    policy: RetryPolicy,
    fixed_clock: datetime,
) -> Iterator[ClientBuilder]:
    clients: list[Client] = []

    def build(
        outcomes: tuple[Outcome, ...],
    ) -> tuple[RetryingProviderClient, FakeProvider, list[float]]:
        client, provider, waits = build_client(outcomes, policy, fixed_clock)
        clients.append(client.http)
        return client, provider, waits

    yield build
    for http in clients:
        http.close()
