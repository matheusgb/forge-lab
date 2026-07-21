import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from retry_client.client import RetryingProviderClient, TimeoutSettings
from retry_client.model import CallReport, Operation, RetryPolicy
from retry_client.provider import FakeProvider, Outcome
from retry_client.timing import FixedClock, FixedRandom, RecordingWait


@dataclass(frozen=True)
class ExperimentCase:
    name: str
    operation: Operation
    outcomes: tuple[Outcome, ...]


@dataclass(frozen=True)
class Scenario:
    name: str
    random_value: float
    policy: RetryPolicy
    cases: tuple[ExperimentCase, ...]


def parse_outcome(raw: dict[str, object]) -> Outcome:
    if raw.get("timeout") is True:
        return Outcome.timeout()
    status = cast(int, raw["status"])
    retry_after_value = raw.get("retry_after")
    retry_after = None if retry_after_value is None else str(retry_after_value)
    return Outcome.response(status, retry_after=retry_after)


def load_scenario(path: Path) -> Scenario:
    raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    policy_data = cast(dict[str, object], raw["policy"])
    cases_data = cast(list[dict[str, object]], raw["cases"])
    policy = RetryPolicy(
        max_attempts=cast(int, policy_data["max_attempts"]),
        base_delay_seconds=cast(float, policy_data["base_delay_seconds"]),
        max_delay_seconds=cast(float, policy_data["max_delay_seconds"]),
        jitter_ratio=cast(float, policy_data["jitter_ratio"]),
    )
    cases = tuple(
        ExperimentCase(
            name=str(case["name"]),
            operation=Operation(str(case["operation"])),
            outcomes=tuple(
                parse_outcome(outcome)
                for outcome in cast(list[dict[str, object]], case["outcomes"])
            ),
        )
        for case in cases_data
    )
    return Scenario(
        name=str(raw["name"]),
        random_value=cast(float, raw["random_value"]),
        policy=policy,
        cases=cases,
    )


def format_report(name: str, report: CallReport, waits: list[float]) -> str:
    attempts = ", ".join(attempt.outcome for attempt in report.attempts)
    wait_text = ", ".join(f"{value:.2f}s" for value in waits) or "nenhuma"
    return (
        f"{name}: operação={report.operation.value}; tentativas=[{attempts}]; "
        f"esperas=[{wait_text}]; decisão={report.final_decision.value}"
    )


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    lines = [f"Cenário: {scenario.name}"]

    for case in scenario.cases:
        provider = FakeProvider(case.outcomes)
        wait = RecordingWait()
        with RetryingProviderClient(
            transport=provider.transport(),
            policy=scenario.policy,
            timeout=TimeoutSettings(),
            clock=FixedClock(datetime(2026, 7, 21, 12, tzinfo=UTC)),
            wait=wait,
            random_value=FixedRandom(scenario.random_value),
        ) as client:
            report = client.call(case.operation)
            lines.append(format_report(case.name, report, wait.calls))

    output = "\n".join(lines)
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
