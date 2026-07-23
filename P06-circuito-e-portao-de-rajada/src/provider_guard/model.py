from enum import StrEnum

from pydantic import BaseModel, ConfigDict, PositiveFloat, PositiveInt


class ProviderOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class CircuitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    failure_threshold: PositiveInt = 3
    recovery_timeout_seconds: PositiveFloat = 5.0


class TokenBucketPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    capacity: PositiveInt = 3
    refill_rate_per_second: PositiveFloat = 1.0
