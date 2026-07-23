from datetime import UTC, datetime
from pathlib import Path

from httpx2 import Client, Timeout
from pydantic import BaseModel, ConfigDict, Field

from retry_client.client import RetryingProviderClient
from retry_client.model import CallResult, Operation, RetryPolicy
from retry_client.provider import FakeProvider, Outcome


class ExperimentCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    operation: Operation
    outcomes: tuple[Outcome, ...]


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    random_value: float = Field(ge=0, le=1)
    policy: RetryPolicy
    cases: tuple[ExperimentCase, ...]


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate_json(path.read_text(encoding="utf-8"))


def format_report(
    name: str,
    result: CallResult,
    outcomes: tuple[Outcome, ...],
    attempts: int,
    waits: list[float],
) -> str:
    attempted = ", ".join(outcome.label for outcome in outcomes[:attempts])
    wait_text = ", ".join(f"{seconds:.2f}s" for seconds in waits) or "nenhuma"
    return (
        f"{name}: operação={result.operation.value}; tentativas=[{attempted}]; "
        f"esperas=[{wait_text}]; decisão={result.final_decision.value}"
    )


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    lines = [f"Cenário: {scenario.name}"]

    for case in scenario.cases:
        provider = FakeProvider(case.outcomes)
        waits: list[float] = []
        with Client(
            base_url="https://provider.test",
            transport=provider.transport(),
            timeout=Timeout(connect=0.2, read=0.5, write=0.5, pool=0.2),
        ) as http:
            client = RetryingProviderClient(
                http=http,
                policy=scenario.policy,
                clock=lambda: datetime(2026, 7, 21, 12, tzinfo=UTC),
                wait=waits.append,
                random_value=lambda: scenario.random_value,
            )
            result = client.call(case.operation)
            lines.append(format_report(case.name, result, case.outcomes, provider.attempts, waits))

    output = "\n".join(lines)
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
