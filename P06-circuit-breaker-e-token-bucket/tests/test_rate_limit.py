from datetime import timedelta
from time import time

import time_machine

from provider_guard.model import TokenBucketPolicy
from provider_guard.rate_limit import TokenBucket


def test_burst_is_limited_and_elapsed_time_refills(
    bucket_policy: TokenBucketPolicy,
) -> None:
    with time_machine.travel("2026-07-22T12:00:00Z", tick=False) as clock:
        bucket = TokenBucket(policy=bucket_policy, clock=time)

        assert [bucket.consume() for _ in range(5)] == [True, True, True, False, False]
        clock.shift(timedelta(seconds=1.5))
        assert bucket.available_tokens == 1.5
        assert bucket.consume()
        assert bucket.available_tokens == 0.5


def test_refill_never_exceeds_capacity(bucket_policy: TokenBucketPolicy) -> None:
    with time_machine.travel("2026-07-22T12:00:00Z", tick=False) as clock:
        bucket = TokenBucket(policy=bucket_policy, clock=time)
        for _ in range(bucket_policy.capacity):
            assert bucket.consume()

        clock.shift(timedelta(seconds=100))
        assert bucket.available_tokens == float(bucket_policy.capacity)
