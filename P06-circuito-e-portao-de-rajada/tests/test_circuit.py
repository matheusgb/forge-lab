import pytest

from provider_guard.circuit import CircuitBreaker
from provider_guard.errors import CircuitOpenError, ProviderUnavailable
from provider_guard.model import CircuitPolicy, CircuitState
from provider_guard.timing import ManualClock


def controlled_failure() -> str:
    raise ProviderUnavailable("controlled failure")


def test_circuit_starts_closed(
    circuit_policy: CircuitPolicy,
    clock: ManualClock,
) -> None:
    circuit = CircuitBreaker(policy=circuit_policy, clock=clock)

    assert circuit.snapshot.state is CircuitState.CLOSED
    assert circuit.snapshot.consecutive_failures == 0
    assert circuit.snapshot.opened_at is None


def test_failure_threshold_opens_and_rejects_without_calling_operation(
    circuit_policy: CircuitPolicy,
    clock: ManualClock,
) -> None:
    circuit = CircuitBreaker(policy=circuit_policy, clock=clock)
    calls = 0

    def fail() -> str:
        nonlocal calls
        calls += 1
        return controlled_failure()

    for _ in range(circuit_policy.failure_threshold):
        with pytest.raises(ProviderUnavailable):
            circuit.execute(fail)

    with pytest.raises(CircuitOpenError) as error:
        circuit.execute(fail)

    assert calls == 3
    assert circuit.state is CircuitState.OPEN
    assert error.value.retry_after_seconds == 5.0


def test_failure_then_success_resets_consecutive_failures(
    circuit_policy: CircuitPolicy,
    clock: ManualClock,
) -> None:
    circuit = CircuitBreaker(policy=circuit_policy, clock=clock)

    with pytest.raises(ProviderUnavailable):
        circuit.execute(controlled_failure)

    assert circuit.snapshot.consecutive_failures == 1
    assert circuit.execute(lambda: "ok") == "ok"
    assert circuit.snapshot.consecutive_failures == 0
    assert circuit.state is CircuitState.CLOSED


def test_half_open_failure_reopens_and_later_success_closes(
    circuit_policy: CircuitPolicy,
    clock: ManualClock,
) -> None:
    circuit = CircuitBreaker(policy=circuit_policy, clock=clock)

    for _ in range(circuit_policy.failure_threshold):
        with pytest.raises(ProviderUnavailable):
            circuit.execute(controlled_failure)

    clock.advance(circuit_policy.recovery_timeout_seconds)
    with pytest.raises(ProviderUnavailable):
        circuit.execute(controlled_failure)

    assert circuit.state is CircuitState.OPEN
    assert circuit.snapshot.opened_at == 5.0

    clock.advance(circuit_policy.recovery_timeout_seconds)
    assert circuit.execute(lambda: "recovered") == "recovered"
    assert circuit.state is CircuitState.CLOSED
    assert circuit.snapshot.consecutive_failures == 0


def test_half_open_accepts_only_one_probe(
    clock: ManualClock,
) -> None:
    circuit = CircuitBreaker(
        policy=CircuitPolicy(failure_threshold=1, recovery_timeout_seconds=1.0),
        clock=clock,
    )
    with pytest.raises(ProviderUnavailable):
        circuit.execute(controlled_failure)
    clock.advance(1.0)

    def nested_call() -> str:
        return circuit.execute(lambda: "nested")

    with pytest.raises(CircuitOpenError) as error:
        circuit.execute(nested_call)

    assert error.value.reason == "half_open_probe_in_flight"
    assert circuit.state is CircuitState.HALF_OPEN
    assert circuit.execute(lambda: "single-probe") == "single-probe"
    assert circuit.state is CircuitState.CLOSED


def test_circuit_policy_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        CircuitPolicy(failure_threshold=0)
    with pytest.raises(ValueError):
        CircuitPolicy(recovery_timeout_seconds=0)
