import json
import logging
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import cast

from provider_guard.circuit import CircuitBreaker
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.errors import CircuitOpenError, ProviderUnavailable, RateLimitExceeded
from provider_guard.model import CircuitPolicy, CircuitState, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket
from provider_guard.timing import ManualClock


@dataclass(frozen=True)
class Scenario:
    name: str
    secret_env_var: str
    circuit_policy: CircuitPolicy
    bucket_policy: TokenBucketPolicy
    failure_outcomes: tuple[ProviderOutcome, ...]
    burst_outcomes: tuple[ProviderOutcome, ...]
    burst_volume: int


def load_scenario(path: Path) -> Scenario:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    circuit_data = cast(dict[str, object], raw["circuit"])
    bucket_data = cast(dict[str, object], raw["token_bucket"])
    failure_data = cast(dict[str, object], raw["failure"])
    burst_data = cast(dict[str, object], raw["burst"])
    return Scenario(
        name=str(raw["name"]),
        secret_env_var=str(raw["secret_env_var"]),
        circuit_policy=CircuitPolicy(
            failure_threshold=cast(int, circuit_data["failure_threshold"]),
            recovery_timeout_seconds=cast(float, circuit_data["recovery_timeout_seconds"]),
        ),
        bucket_policy=TokenBucketPolicy(
            capacity=cast(int, bucket_data["capacity"]),
            refill_rate_per_second=cast(float, bucket_data["refill_rate_per_second"]),
        ),
        failure_outcomes=tuple(
            ProviderOutcome(str(value)) for value in cast(list[object], failure_data["outcomes"])
        ),
        burst_outcomes=tuple(
            ProviderOutcome(str(value)) for value in cast(list[object], burst_data["outcomes"])
        ),
        burst_volume=cast(int, burst_data["volume"]),
    )


def build_client(
    *,
    config: ProviderConfig,
    outcomes: tuple[ProviderOutcome, ...],
    scenario: Scenario,
    clock: ManualClock,
) -> tuple[ProtectedProviderClient, FakeProvider, CircuitBreaker, TokenBucket]:
    provider = FakeProvider(outcomes=outcomes, expected_api_key=config.api_key)
    circuit = CircuitBreaker(policy=scenario.circuit_policy, clock=clock)
    bucket = TokenBucket(policy=scenario.bucket_policy, clock=clock)
    client = ProtectedProviderClient(
        config=config,
        provider=provider,
        circuit=circuit,
        bucket=bucket,
    )
    return client, provider, circuit, bucket


def call_result(client: ProtectedProviderClient) -> str:
    try:
        client.fetch()
    except ProviderUnavailable:
        return "provider_failure"
    except CircuitOpenError:
        return "circuit_rejected"
    except RateLimitExceeded:
        return "rate_limited"
    return "success"


def observation(
    *,
    label: str,
    result: str,
    clock: ManualClock,
    provider: FakeProvider,
    circuit: CircuitBreaker,
    bucket: TokenBucket,
) -> str:
    snapshot = circuit.snapshot
    return (
        f"t={clock():.1f}s ação={label} resultado={result} "
        f"estado={snapshot.state.value} falhas={snapshot.consecutive_failures} "
        f"chamadas_provider={provider.calls} tokens={bucket.available_tokens:.1f}"
    )


def require_circuit_state(circuit: CircuitBreaker, expected: CircuitState) -> None:
    if circuit.state is not expected:
        raise AssertionError(
            f"unexpected circuit state: expected={expected.value} actual={circuit.state.value}"
        )


def run_circuit_experiment(
    scenario: Scenario,
    config: ProviderConfig,
) -> list[str]:
    clock = ManualClock()
    client, provider, circuit, bucket = build_client(
        config=config,
        outcomes=scenario.failure_outcomes,
        scenario=scenario,
        clock=clock,
    )
    lines = ["Circuito:"]

    for number in range(1, scenario.circuit_policy.failure_threshold + 1):
        result = call_result(client)
        lines.append(
            observation(
                label=f"falha-{number}",
                result=result,
                clock=clock,
                provider=provider,
                circuit=circuit,
                bucket=bucket,
            )
        )

    result = call_result(client)
    lines.append(
        observation(
            label="chamada-imediata",
            result=result,
            clock=clock,
            provider=provider,
            circuit=circuit,
            bucket=bucket,
        )
    )
    if provider.calls != scenario.circuit_policy.failure_threshold:
        raise AssertionError("open circuit forwarded a call to the provider")

    clock.advance(scenario.circuit_policy.recovery_timeout_seconds)
    result = call_result(client)
    lines.append(
        observation(
            label="sonda-half-open-com-falha",
            result=result,
            clock=clock,
            provider=provider,
            circuit=circuit,
            bucket=bucket,
        )
    )
    require_circuit_state(circuit, CircuitState.OPEN)

    clock.advance(scenario.circuit_policy.recovery_timeout_seconds)
    result = call_result(client)
    lines.append(
        observation(
            label="sonda-half-open-com-sucesso",
            result=result,
            clock=clock,
            provider=provider,
            circuit=circuit,
            bucket=bucket,
        )
    )
    require_circuit_state(circuit, CircuitState.CLOSED)
    return lines


def run_burst_experiment(
    scenario: Scenario,
    config: ProviderConfig,
) -> list[str]:
    clock = ManualClock()
    client, provider, circuit, bucket = build_client(
        config=config,
        outcomes=scenario.burst_outcomes,
        scenario=scenario,
        clock=clock,
    )
    results = [call_result(client) for _ in range(scenario.burst_volume)]
    accepted = results.count("success")
    rejected = results.count("rate_limited")
    expected_rejected = scenario.burst_volume - scenario.bucket_policy.capacity

    clock.advance(1.0)
    recovered_result = call_result(client)
    if accepted != scenario.bucket_policy.capacity or rejected != expected_rejected:
        raise AssertionError("burst result does not match the configured bucket")
    if recovered_result != "success":
        raise AssertionError("elapsed time did not refill one token")
    require_circuit_state(circuit, CircuitState.CLOSED)

    return [
        "Rajada:",
        (
            f"t=0.0s volume={scenario.burst_volume} permitidas={accepted} "
            f"recusadas={rejected} chamadas_provider={provider.calls - 1}"
        ),
        (
            f"t=1.0s chamada-após-reposição={recovered_result} "
            f"chamadas_provider={provider.calls} tokens={bucket.available_tokens:.1f}"
        ),
    ]


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    controlled_secret = "p06-controlled-secret-for-log-scan"
    config = ProviderConfig.from_env(
        variable_name=scenario.secret_env_var,
        environ={scenario.secret_env_var: controlled_secret},
    )

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    guard_logger = logging.getLogger("provider_guard")
    previous_level = guard_logger.level
    previous_propagate = guard_logger.propagate
    guard_logger.setLevel(logging.INFO)
    guard_logger.propagate = False
    guard_logger.addHandler(handler)
    try:
        lines = [f"Cenário: {scenario.name}"]
        lines.extend(run_circuit_experiment(scenario, config))
        lines.extend(run_burst_experiment(scenario, config))
    finally:
        guard_logger.removeHandler(handler)
        guard_logger.setLevel(previous_level)
        guard_logger.propagate = previous_propagate

    logs = log_stream.getvalue().rstrip()
    if controlled_secret in logs:
        raise AssertionError("controlled secret appeared in captured logs")

    lines.extend(
        [
            "Segredo:",
            "segredo_encontrado_nos_logs=false",
            "Logs capturados:",
            logs,
        ]
    )
    output = "\n".join(lines)
    if controlled_secret in output:
        raise AssertionError("controlled secret appeared in experiment evidence")

    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
