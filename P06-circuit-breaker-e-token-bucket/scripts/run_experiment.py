import logging
from datetime import timedelta
from io import StringIO
from pathlib import Path
from time import time

import time_machine
from pybreaker import CircuitBreaker, CircuitBreakerError
from pydantic import BaseModel, ConfigDict, SecretStr

from provider_guard.circuit import build_circuit
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.errors import ProviderUnavailable, RateLimitExceeded
from provider_guard.model import CircuitPolicy, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket


class OutcomeSequence(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcomes: tuple[ProviderOutcome, ...]


class BurstScenario(OutcomeSequence):
    volume: int


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    circuit: CircuitPolicy
    token_bucket: TokenBucketPolicy
    failure: OutcomeSequence
    burst: BurstScenario


def build_client(
    scenario: Scenario,
    outcomes: tuple[ProviderOutcome, ...],
    secret: str,
) -> tuple[ProtectedProviderClient, FakeProvider, CircuitBreaker, TokenBucket]:
    provider = FakeProvider(outcomes=outcomes, expected_api_key=secret)
    circuit = build_circuit(scenario.circuit)
    bucket = TokenBucket(policy=scenario.token_bucket, clock=time)
    client = ProtectedProviderClient(
        config=ProviderConfig(api_key=SecretStr(secret)),
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
    except CircuitBreakerError:
        return "circuit_rejected"
    except RateLimitExceeded:
        return "rate_limited"
    return "success"


def circuit_experiment(scenario: Scenario, secret: str) -> list[str]:
    lines = ["Circuito:"]

    with time_machine.travel("2026-07-22T12:00:00Z", tick=False) as clock:
        client, provider, circuit, _ = build_client(scenario, scenario.failure.outcomes, secret)
        for attempt in range(1, scenario.circuit.failure_threshold + 1):
            result = call_result(client)
            lines.append(
                f"falha-{attempt}: resultado={result} estado={circuit.current_state} "
                f"chamadas_provider={provider.calls}"
            )

        result = call_result(client)
        lines.append(
            f"chamada-imediata: resultado={result} estado={circuit.current_state} "
            f"chamadas_provider={provider.calls}"
        )

        clock.shift(timedelta(seconds=scenario.circuit.recovery_timeout_seconds))
        lines.append(
            f"sonda-com-falha: resultado={call_result(client)} estado={circuit.current_state}"
        )

        clock.shift(timedelta(seconds=scenario.circuit.recovery_timeout_seconds))
        lines.append(
            f"sonda-com-sucesso: resultado={call_result(client)} estado={circuit.current_state}"
        )

    return lines


def burst_experiment(scenario: Scenario, secret: str) -> list[str]:
    with time_machine.travel("2026-07-22T12:00:00Z", tick=False) as clock:
        client, provider, _, bucket = build_client(scenario, scenario.burst.outcomes, secret)
        results = [call_result(client) for _ in range(scenario.burst.volume)]
        clock.shift(timedelta(seconds=1))
        recovered = call_result(client)
        remaining_tokens = bucket.available_tokens

    return [
        "Rajada:",
        f"volume={scenario.burst.volume} permitidas={results.count('success')} "
        f"recusadas={results.count('rate_limited')} chamadas_provider={provider.calls - 1}",
        f"após-um-segundo={recovered} tokens={remaining_tokens:.1f}",
    ]


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = Scenario.model_validate_json((project / "scenario.yaml").read_text())
    secret = "p06-controlled-secret-for-log-scan"
    log_stream = StringIO()
    logging.basicConfig(level=logging.INFO, stream=log_stream, format="%(levelname)s %(message)s")

    lines = [f"Cenário: {scenario.name}"]
    lines.extend(circuit_experiment(scenario, secret))
    lines.extend(burst_experiment(scenario, secret))

    logs = log_stream.getvalue().rstrip()
    if secret in logs:
        raise AssertionError("controlled secret appeared in captured logs")
    lines.extend(["Segredo:", "segredo_encontrado_nos_logs=false", "Logs capturados:", logs])

    output = "\n".join(lines)
    (project / "evidence" / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
