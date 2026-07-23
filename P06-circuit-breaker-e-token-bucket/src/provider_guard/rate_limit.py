from collections.abc import Callable
from time import monotonic

from provider_guard.model import TokenBucketPolicy


class TokenBucket:
    def __init__(
        self,
        *,
        policy: TokenBucketPolicy,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = policy
        self.clock = clock
        self._tokens = float(policy.capacity)
        self._updated_at = clock()

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._tokens

    def consume(self, amount: float = 1.0) -> bool:
        if amount <= 0:
            raise ValueError("token amount must be positive")
        self._refill()
        if self._tokens < amount:
            return False
        self._tokens -= amount
        return True

    def _refill(self) -> None:
        now = self.clock()
        elapsed = now - self._updated_at
        if elapsed < 0:
            raise ValueError("clock must be monotonic")
        self._tokens = min(
            float(self.policy.capacity),
            self._tokens + elapsed * self.policy.refill_rate_per_second,
        )
        self._updated_at = now
