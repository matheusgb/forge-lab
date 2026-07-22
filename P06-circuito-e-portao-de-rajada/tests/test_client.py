import pytest

from provider_guard.circuit import CircuitBreaker
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.errors import (
    CircuitOpenError,
    ProviderAuthenticationError,
    ProviderUnavailable,
    RateLimitExceeded,
)
from provider_guard.model import CircuitPolicy, CircuitState, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket
from provider_guard.timing import ManualClock


def build_client(
    *,
    outcomes: tuple[ProviderOutcome, ...],
    clock: ManualClock,
    secret: str = "controlled-secret",
    expected_secret: str | None = None,
    failure_threshold: int = 3,
    capacity: int = 3,
) -> tuple[ProtectedProviderClient, FakeProvider, CircuitBreaker, TokenBucket]:
    config = ProviderConfig(endpoint="https://provider.test", api_key=secret)
    provider = FakeProvider(
        outcomes=outcomes,
        expected_api_key=secret if expected_secret is None else expected_secret,
    )
    circuit = CircuitBreaker(
        policy=CircuitPolicy(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=5.0,
        ),
        clock=clock,
    )
    bucket = TokenBucket(
        policy=TokenBucketPolicy(capacity=capacity, refill_rate_per_second=1.0),
        clock=clock,
    )
    client = ProtectedProviderClient(
        config=config,
        provider=provider,
        circuit=circuit,
        bucket=bucket,
    )
    return client, provider, circuit, bucket


def test_client_sends_the_configured_credential(clock: ManualClock) -> None:
    client, provider, circuit, _ = build_client(
        outcomes=(ProviderOutcome.SUCCESS,),
        clock=clock,
    )

    assert client.fetch() == "resource-1"
    assert provider.calls == 1
    assert circuit.state is CircuitState.CLOSED


def test_rate_limit_rejection_does_not_count_as_provider_failure(
    clock: ManualClock,
) -> None:
    client, provider, circuit, _ = build_client(
        outcomes=(ProviderOutcome.SUCCESS,),
        clock=clock,
        failure_threshold=1,
        capacity=1,
    )
    client.fetch()

    with pytest.raises(RateLimitExceeded):
        client.fetch()

    assert provider.calls == 1
    assert circuit.state is CircuitState.CLOSED
    assert circuit.snapshot.consecutive_failures == 0


def test_open_circuit_rejection_does_not_consume_a_token(clock: ManualClock) -> None:
    client, provider, circuit, bucket = build_client(
        outcomes=(ProviderOutcome.FAILURE,),
        clock=clock,
        failure_threshold=1,
        capacity=2,
    )
    with pytest.raises(ProviderUnavailable):
        client.fetch()
    tokens_before_rejection = bucket.available_tokens

    with pytest.raises(CircuitOpenError):
        client.fetch()

    assert provider.calls == 1
    assert circuit.state is CircuitState.OPEN
    assert bucket.available_tokens == tokens_before_rejection


def test_authentication_failure_does_not_open_the_circuit(clock: ManualClock) -> None:
    client, provider, circuit, _ = build_client(
        outcomes=(ProviderOutcome.SUCCESS,),
        clock=clock,
        secret="wrong-secret",
        expected_secret="expected-secret",
        failure_threshold=1,
    )

    with pytest.raises(ProviderAuthenticationError):
        client.fetch()

    assert provider.calls == 1
    assert circuit.state is CircuitState.CLOSED
    assert circuit.snapshot.consecutive_failures == 0
