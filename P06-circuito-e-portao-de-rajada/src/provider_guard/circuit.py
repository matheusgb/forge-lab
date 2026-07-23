import logging
from typing import Any

from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerState

from provider_guard.errors import ProviderUnavailable
from provider_guard.model import CircuitPolicy

logger = logging.getLogger(__name__)


class TransitionLogger(CircuitBreakerListener):
    def state_change(
        self,
        cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        previous = old_state.name if old_state is not None else "none"
        logger.info("circuit_transition previous=%s current=%s", previous, new_state.name)

    def failure(self, cb: CircuitBreaker, exc: BaseException) -> None:
        logger.info("circuit_failure count=%d", cb.fail_counter)

    def success(self, cb: CircuitBreaker) -> None:
        if cb.current_state == "half-open":
            logger.info("circuit_probe_succeeded")


def build_circuit(policy: CircuitPolicy) -> CircuitBreaker:
    def ignore_non_provider_failures(error: Any) -> bool:
        return not isinstance(error, ProviderUnavailable)

    return CircuitBreaker(
        fail_max=policy.failure_threshold,
        reset_timeout=policy.recovery_timeout_seconds,
        exclude=[ignore_non_provider_failures],
        listeners=[TransitionLogger()],
        name="provider",
        throw_new_error_on_trip=False,
    )
