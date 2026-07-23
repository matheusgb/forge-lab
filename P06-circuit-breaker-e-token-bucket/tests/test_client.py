import pytest
from pybreaker import CircuitBreaker, CircuitBreakerError
from pydantic import SecretStr

from provider_guard.circuit import build_circuit
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.errors import (
    ProviderAuthenticationError,
    ProviderUnavailable,
    RateLimitExceeded,
)
from provider_guard.model import CircuitPolicy, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket


def build_client(
    outcomes: tuple[ProviderOutcome, ...],
    *,
    expected_secret: str = "controlled-secret",
    capacity: int = 3,
) -> tuple[ProtectedProviderClient, FakeProvider, CircuitBreaker, TokenBucket]:
    secret = "controlled-secret"
    provider = FakeProvider(outcomes=outcomes, expected_api_key=expected_secret)
    circuit = build_circuit(CircuitPolicy(failure_threshold=1, recovery_timeout_seconds=5))
    bucket = TokenBucket(
        policy=TokenBucketPolicy(capacity=capacity, refill_rate_per_second=1),
        clock=lambda: 0.0,
    )
    client = ProtectedProviderClient(
        config=ProviderConfig(api_key=SecretStr(secret)),
        provider=provider,
        circuit=circuit,
        bucket=bucket,
    )
    return client, provider, circuit, bucket


def test_open_circuit_rejection_does_not_reach_provider_or_consume_token() -> None:
    client, provider, circuit, bucket = build_client((ProviderOutcome.FAILURE,), capacity=2)

    with pytest.raises(ProviderUnavailable):
        client.fetch()
    tokens_before_rejection = bucket.available_tokens

    with pytest.raises(CircuitBreakerError):
        client.fetch()

    assert provider.calls == 1
    assert circuit.current_state == "open"
    assert bucket.available_tokens == tokens_before_rejection


def test_local_limit_does_not_open_circuit() -> None:
    client, provider, circuit, _ = build_client((ProviderOutcome.SUCCESS,), capacity=1)
    assert client.fetch() == "resource-1"

    with pytest.raises(RateLimitExceeded):
        client.fetch()

    assert provider.calls == 1
    assert circuit.current_state == "closed"


def test_authentication_error_does_not_open_circuit() -> None:
    client, provider, circuit, _ = build_client(
        (ProviderOutcome.SUCCESS,), expected_secret="different-secret"
    )

    with pytest.raises(ProviderAuthenticationError):
        client.fetch()

    assert provider.calls == 1
    assert circuit.current_state == "closed"
