import pytest

from provider_guard.model import TokenBucketPolicy
from provider_guard.rate_limit import TokenBucket
from provider_guard.timing import ManualClock


def test_burst_accepts_capacity_and_rejects_the_rest(
    bucket_policy: TokenBucketPolicy,
    clock: ManualClock,
) -> None:
    bucket = TokenBucket(policy=bucket_policy, clock=clock)

    decisions = [bucket.consume() for _ in range(5)]

    assert decisions == [True, True, True, False, False]
    assert bucket.available_tokens == 0.0


def test_elapsed_time_refills_tokens_without_exceeding_capacity(
    bucket_policy: TokenBucketPolicy,
    clock: ManualClock,
) -> None:
    bucket = TokenBucket(policy=bucket_policy, clock=clock)
    for _ in range(bucket_policy.capacity):
        assert bucket.consume()

    clock.advance(1.5)
    assert bucket.available_tokens == 1.5
    assert bucket.consume()
    assert bucket.available_tokens == 0.5

    clock.advance(100.0)
    assert bucket.available_tokens == float(bucket_policy.capacity)


def test_bucket_rejects_non_positive_cost(
    bucket_policy: TokenBucketPolicy,
    clock: ManualClock,
) -> None:
    bucket = TokenBucket(policy=bucket_policy, clock=clock)

    with pytest.raises(ValueError):
        bucket.consume(0)


def test_bucket_rejects_a_clock_that_moves_backwards() -> None:
    now = 2.0
    bucket = TokenBucket(
        policy=TokenBucketPolicy(),
        clock=lambda: now,
    )
    now = 1.0

    with pytest.raises(ValueError):
        bucket.consume()


def test_bucket_policy_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        TokenBucketPolicy(capacity=0)
    with pytest.raises(ValueError):
        TokenBucketPolicy(refill_rate_per_second=0)
