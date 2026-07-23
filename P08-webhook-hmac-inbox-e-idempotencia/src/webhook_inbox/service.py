from collections.abc import Callable
from datetime import UTC, datetime

from webhook_inbox.contract import parse_event
from webhook_inbox.errors import InvalidSignatureError, ReplayRejectedError
from webhook_inbox.model import ReceiveResult
from webhook_inbox.repository import InMemoryInbox
from webhook_inbox.signing import sign_payload, signatures_match

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class WebhookReceiver:
    def __init__(
        self,
        *,
        secret: str,
        clock: Clock,
        inbox: InMemoryInbox,
        replay_window_seconds: int = 300,
    ) -> None:
        if not secret:
            raise ValueError("secret não pode ser vazio")
        if replay_window_seconds <= 0:
            raise ValueError("replay_window_seconds precisa ser positivo")
        self._secret = secret
        self._clock = clock
        self._inbox = inbox
        self._replay_window_seconds = replay_window_seconds

    def receive(
        self,
        *,
        raw_body: bytes,
        timestamp_header: str | None,
        signature_header: str | None,
    ) -> ReceiveResult:
        try:
            timestamp = int(timestamp_header) if timestamp_header is not None else None
        except ValueError as error:
            raise InvalidSignatureError("timestamp inválido") from error
        if timestamp is None or signature_header is None:
            raise InvalidSignatureError("timestamp e assinatura são obrigatórios")

        now = self._clock()
        now_timestamp = int(now.timestamp())
        if abs(now_timestamp - timestamp) > self._replay_window_seconds:
            raise ReplayRejectedError("timestamp fora da janela aceita")

        expected = sign_payload(self._secret, timestamp, raw_body)
        if not signatures_match(expected, signature_header):
            raise InvalidSignatureError("assinatura inválida")

        event = parse_event(raw_body)
        return self._inbox.save_received(
            event=event,
            raw_body=raw_body,
            received_at=now,
        )
