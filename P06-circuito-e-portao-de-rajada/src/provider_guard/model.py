from dataclasses import dataclass
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ProviderOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class CircuitPolicy:
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least one")
        if self.recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive")


@dataclass(frozen=True)
class TokenBucketPolicy:
    capacity: int = 3
    refill_rate_per_second: float = 1.0

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be at least one")
        if self.refill_rate_per_second <= 0:
            raise ValueError("refill_rate_per_second must be positive")


@dataclass(frozen=True)
class CircuitSnapshot:
    state: CircuitState
    consecutive_failures: int
    opened_at: float | None
