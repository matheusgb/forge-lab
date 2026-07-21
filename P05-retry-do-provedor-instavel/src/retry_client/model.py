from dataclasses import dataclass
from enum import StrEnum


class Operation(StrEnum):
    SAFE_READ = "safe_read"
    UNSAFE_CREATE = "unsafe_create"

    @property
    def method(self) -> str:
        if self is Operation.SAFE_READ:
            return "GET"
        return "POST"

    @property
    def retry_safe(self) -> bool:
        return self is Operation.SAFE_READ


class Decision(StrEnum):
    SUCCESS = "success"
    RETRY_TRANSIENT = "retry_transient"
    STOP_PERMANENT = "stop_permanent"
    STOP_UNSAFE = "stop_unsafe"
    STOP_EXHAUSTED = "stop_exhausted"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 5.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must not be negative")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must not be smaller than base delay")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between zero and one")


@dataclass(frozen=True)
class AttemptRecord:
    number: int
    outcome: str
    decision: Decision
    wait_seconds: float | None = None


@dataclass(frozen=True)
class CallReport:
    operation: Operation
    attempts: tuple[AttemptRecord, ...]
    final_status: int | None

    @property
    def final_decision(self) -> Decision:
        return self.attempts[-1].decision
