from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator


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


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: PositiveInt = 3
    base_delay_seconds: Annotated[float, Field(ge=0)] = 0.5
    max_delay_seconds: Annotated[float, Field(ge=0)] = 5.0
    jitter_ratio: Annotated[float, Field(ge=0, le=1)] = 0.2

    @model_validator(mode="after")
    def delay_order(self) -> Self:
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must not be smaller than base delay")
        return self


@dataclass(frozen=True)
class CallResult:
    operation: Operation
    final_decision: Decision
    final_status: int | None
