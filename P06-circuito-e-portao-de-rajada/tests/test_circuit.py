from datetime import timedelta

import pytest
import time_machine
from pybreaker import CircuitBreakerError

from provider_guard.circuit import build_circuit
from provider_guard.errors import ProviderUnavailable
from provider_guard.model import CircuitPolicy


def fail() -> str:
    raise ProviderUnavailable("controlled failure")


def test_threshold_opens_and_rejects_without_calling_provider(
    circuit_policy: CircuitPolicy,
) -> None:
    circuit = build_circuit(circuit_policy)
    calls = 0

    def counted_failure() -> str:
        nonlocal calls
        calls += 1
        return fail()

    with time_machine.travel("2026-07-22T12:00:00Z", tick=False):
        for _ in range(circuit_policy.failure_threshold):
            with pytest.raises(ProviderUnavailable):
                circuit.call(counted_failure)

        with pytest.raises(CircuitBreakerError):
            circuit.call(counted_failure)

    assert calls == 3
    assert circuit.current_state == "open"
    assert circuit.fail_counter == 3


def test_failed_probe_reopens_and_next_success_closes(
    circuit_policy: CircuitPolicy,
) -> None:
    circuit = build_circuit(circuit_policy)

    with time_machine.travel("2026-07-22T12:00:00Z", tick=False) as clock:
        for _ in range(circuit_policy.failure_threshold):
            with pytest.raises(ProviderUnavailable):
                circuit.call(fail)

        clock.shift(timedelta(seconds=circuit_policy.recovery_timeout_seconds))
        with pytest.raises(ProviderUnavailable):
            circuit.call(fail)
        assert circuit.current_state == "open"

        clock.shift(timedelta(seconds=circuit_policy.recovery_timeout_seconds))
        assert circuit.call(lambda: "recovered") == "recovered"

    assert circuit.current_state == "closed"
    assert circuit.fail_counter == 0


def test_only_provider_unavailability_counts_as_failure() -> None:
    circuit = build_circuit(CircuitPolicy(failure_threshold=1, recovery_timeout_seconds=1))

    with pytest.raises(ValueError):
        circuit.call(lambda: (_ for _ in ()).throw(ValueError("business error")))

    assert circuit.current_state == "closed"
    assert circuit.fail_counter == 0
