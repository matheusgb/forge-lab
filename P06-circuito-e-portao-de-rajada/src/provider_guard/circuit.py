import logging
from collections.abc import Callable
from typing import TypeVar

from provider_guard.errors import CircuitOpenError, ProviderUnavailable
from provider_guard.model import CircuitPolicy, CircuitSnapshot, CircuitState
from provider_guard.timing import Clock

logger = logging.getLogger(__name__)

ResultT = TypeVar("ResultT")


class CircuitBreaker:
    def __init__(self, *, policy: CircuitPolicy, clock: Clock) -> None:
        self.policy = policy
        self.clock = clock
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def snapshot(self) -> CircuitSnapshot:
        return CircuitSnapshot(
            state=self._state,
            consecutive_failures=self._consecutive_failures,
            opened_at=self._opened_at,
        )

    def execute(self, operation: Callable[[], ResultT]) -> ResultT:
        is_probe = self._before_call()
        try:
            result = operation()
        except ProviderUnavailable:
            self._record_failure()
            raise
        except Exception:
            self._record_neutral_result(is_probe=is_probe)
            raise
        self._record_success()
        return result

    def _before_call(self) -> bool:
        if self._state is CircuitState.OPEN:
            remaining = self._remaining_open_seconds()
            if remaining > 0:
                logger.info(
                    "circuit_rejected state=%s retry_after=%.2f",
                    self._state.value,
                    remaining,
                )
                raise CircuitOpenError(remaining)
            self._transition_to_half_open()

        if self._state is CircuitState.HALF_OPEN:
            if self._probe_in_flight:
                logger.info("circuit_rejected state=%s reason=probe_in_flight", self._state.value)
                raise CircuitOpenError(0.0, reason="half_open_probe_in_flight")
            self._probe_in_flight = True
            logger.info("circuit_probe_started state=%s", self._state.value)
            return True

        return False

    def _remaining_open_seconds(self) -> float:
        if self._opened_at is None:
            raise AssertionError("open circuit has no opening timestamp")
        elapsed = self.clock() - self._opened_at
        return max(0.0, self.policy.recovery_timeout_seconds - elapsed)

    def _record_failure(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            self._consecutive_failures = self.policy.failure_threshold
            self._open()
            return

        self._consecutive_failures += 1
        logger.info(
            "circuit_failure state=%s consecutive_failures=%d threshold=%d",
            self._state.value,
            self._consecutive_failures,
            self.policy.failure_threshold,
        )
        if self._consecutive_failures >= self.policy.failure_threshold:
            self._open()

    def _record_success(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            self._close()
            return
        if self._consecutive_failures:
            logger.info("circuit_failure_count_reset previous=%d", self._consecutive_failures)
        self._consecutive_failures = 0

    def _record_neutral_result(self, *, is_probe: bool) -> None:
        if is_probe:
            self._probe_in_flight = False
            logger.info("circuit_probe_cancelled state=%s", self._state.value)

    def _open(self) -> None:
        previous = self._state
        self._state = CircuitState.OPEN
        self._opened_at = self.clock()
        self._probe_in_flight = False
        logger.info(
            "circuit_transition previous=%s current=%s",
            previous.value,
            self._state.value,
        )

    def _transition_to_half_open(self) -> None:
        previous = self._state
        self._state = CircuitState.HALF_OPEN
        self._probe_in_flight = False
        logger.info(
            "circuit_transition previous=%s current=%s",
            previous.value,
            self._state.value,
        )

    def _close(self) -> None:
        previous = self._state
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = None
        self._probe_in_flight = False
        logger.info(
            "circuit_transition previous=%s current=%s",
            previous.value,
            self._state.value,
        )
