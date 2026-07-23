from pathlib import Path

from pydantic import AwareDatetime, BaseModel, PositiveInt, SecretStr

from webhook_inbox.api import AppContainer, build_container
from webhook_inbox.errors import InvalidSignatureError, ReplayRejectedError, SimulatedCrash
from webhook_inbox.model import CrashPoint, WebhookEvent
from webhook_inbox.signing import sign_payload


class EventScenarios(BaseModel):
    authorized: WebhookEvent
    captured_out_of_order: WebhookEvent


class Scenario(BaseModel):
    name: str
    now: AwareDatetime
    replay_window_seconds: PositiveInt
    controlled_secret: SecretStr
    repetitions: PositiveInt
    events: EventScenarios


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate_json(path.read_text(encoding="utf-8"))


def encode(event: WebhookEvent) -> bytes:
    return event.model_dump_json(by_alias=True).encode()


def deliver(container: AppContainer, secret: str, timestamp: int, body: bytes) -> bool:
    result = container.receiver.receive(
        raw_body=body,
        timestamp_header=str(timestamp),
        signature_header=sign_payload(secret, timestamp, body),
    )
    return result.created


def run() -> str:
    project = Path(__file__).resolve().parents[1]
    scenario = load_scenario(project / "scenario.yaml")
    timestamp = int(scenario.now.timestamp())
    secret = scenario.controlled_secret.get_secret_value()
    container = build_container(
        secret=secret,
        clock=lambda: scenario.now,
        replay_window_seconds=scenario.replay_window_seconds,
    )
    authorized = scenario.events.authorized
    authorized_body = encode(authorized)

    deliveries = [
        deliver(container, secret, timestamp, authorized_body) for _ in range(scenario.repetitions)
    ]
    records_after_deliveries = len(container.inbox.all())

    try:
        container.worker.process(
            authorized.event_id,
            crash_at=CrashPoint.BEFORE_EFFECT,
        )
    except SimulatedCrash as error:
        crash_result = str(error)
    else:
        raise AssertionError("o crash controlado deveria interromper o worker")

    status_after_crash = container.inbox.get(authorized.event_id).status.value
    effects_after_crash = len(container.effects.effects)
    recovered = container.worker.process(authorized.event_id)

    altered_body = authorized_body.replace(b"order-1", b"order-altered")
    try:
        container.receiver.receive(
            raw_body=altered_body,
            timestamp_header=str(timestamp),
            signature_header=sign_payload(
                secret,
                timestamp,
                authorized_body,
            ),
        )
    except InvalidSignatureError as error:
        altered_result = str(error)
    else:
        raise AssertionError("o corpo adulterado deveria falhar")

    old_timestamp = timestamp - scenario.replay_window_seconds - 1
    try:
        container.receiver.receive(
            raw_body=authorized_body,
            timestamp_header=str(old_timestamp),
            signature_header=sign_payload(
                secret,
                old_timestamp,
                authorized_body,
            ),
        )
    except ReplayRejectedError as error:
        replay_result = str(error)
    else:
        raise AssertionError("o replay antigo deveria falhar")

    captured = scenario.events.captured_out_of_order
    out_of_order_body = encode(captured)
    deliver(container, secret, timestamp, out_of_order_body)
    out_of_order = container.worker.process(captured.event_id)

    lines = [
        f"Cenário: {scenario.name}",
        f"Três entregas: criadas={deliveries}; registros={records_after_deliveries}",
        f"Crash controlado: {crash_result}",
        f"Depois do crash: status={status_after_crash}; efeitos={effects_after_crash}",
        (
            f"Depois da recuperação: status={recovered.status.value}; "
            f"efeitos={len(container.effects.effects)}"
        ),
        f"Corpo adulterado: {altered_result}",
        f"Replay antigo: {replay_result}",
        f"Fora de ordem: status={out_of_order.status.value}; motivo={out_of_order.failure_reason}",
    ]
    output = "\n".join(lines)
    evidence = project / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "result.txt").write_text(f"{output}\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(run())
