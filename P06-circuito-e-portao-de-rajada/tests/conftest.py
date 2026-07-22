import pytest

from provider_guard.model import CircuitPolicy, TokenBucketPolicy
from provider_guard.timing import ManualClock


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def circuit_policy() -> CircuitPolicy:
    return CircuitPolicy(failure_threshold=3, recovery_timeout_seconds=5.0)


@pytest.fixture
def bucket_policy() -> TokenBucketPolicy:
    return TokenBucketPolicy(capacity=3, refill_rate_per_second=1.0)
