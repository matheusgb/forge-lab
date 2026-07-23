from pydantic import ValidationError

from webhook_inbox.errors import InvalidPayloadError
from webhook_inbox.model import WebhookEvent


def _location(parts: tuple[str | int, ...]) -> str:
    path = "body"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def parse_event(raw_body: bytes) -> WebhookEvent:
    try:
        return WebhookEvent.model_validate_json(raw_body)
    except ValidationError as error:
        detail = error.errors(include_url=False)[0]
        if detail["type"] == "json_invalid":
            message = "corpo JSON inválido"
        elif detail["type"] == "missing":
            message = f"{_location(detail['loc'])}: campo obrigatório ausente"
        else:
            message = f"{_location(detail['loc'])}: {detail['msg']}"
        raise InvalidPayloadError(message) from error
