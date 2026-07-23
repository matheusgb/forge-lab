import os
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from webhook_inbox.errors import (
    DuplicateEventConflictError,
    InvalidPayloadError,
    InvalidSignatureError,
    ReplayRejectedError,
    WebhookError,
)
from webhook_inbox.model import InboxStatus
from webhook_inbox.repository import InMemoryInbox
from webhook_inbox.service import Clock, WebhookReceiver, utc_now
from webhook_inbox.worker import InMemoryEffectStore, WebhookWorker


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    delivery: Literal["accepted", "duplicate"]
    status: InboxStatus


@dataclass(frozen=True)
class AppContainer:
    inbox: InMemoryInbox
    effects: InMemoryEffectStore
    receiver: WebhookReceiver
    worker: WebhookWorker


def build_container(
    *,
    secret: str,
    clock: Clock = utc_now,
    replay_window_seconds: int = 300,
) -> AppContainer:
    inbox = InMemoryInbox()
    effects = InMemoryEffectStore()
    receiver = WebhookReceiver(
        secret=secret,
        clock=clock,
        inbox=inbox,
        replay_window_seconds=replay_window_seconds,
    )
    return AppContainer(
        inbox=inbox,
        effects=effects,
        receiver=receiver,
        worker=WebhookWorker(inbox, effects),
    )


def _error_status(error: WebhookError) -> int:
    if isinstance(error, (InvalidSignatureError, ReplayRejectedError)):
        return 401
    if isinstance(error, InvalidPayloadError):
        return 422
    if isinstance(error, DuplicateEventConflictError):
        return 409
    return 400


def create_app(container: AppContainer) -> FastAPI:
    application = FastAPI(title="P08 Webhook Inbox", version="0.1.0")
    application.state.container = container

    @application.exception_handler(WebhookError)
    async def handle_webhook_error(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        error: WebhookError,
    ) -> JSONResponse:
        return JSONResponse(status_code=_error_status(error), content={"detail": str(error)})

    @application.post(
        "/webhooks/payments",
        response_model=DeliveryResponse,
        status_code=202,
    )
    async def receive_webhook(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        response: Response,
        timestamp_header: Annotated[str | None, Header(alias="X-Webhook-Timestamp")] = None,
        signature_header: Annotated[str | None, Header(alias="X-Webhook-Signature")] = None,
    ) -> DeliveryResponse:
        result = container.receiver.receive(
            raw_body=await request.body(),
            timestamp_header=timestamp_header,
            signature_header=signature_header,
        )
        if not result.created:
            response.status_code = 200
        return DeliveryResponse(
            event_id=result.record.event.event_id,
            delivery="accepted" if result.created else "duplicate",
            status=result.record.status,
        )

    return application


app = create_app(build_container(secret=os.environ.get("P08_WEBHOOK_SECRET", "local-demo-secret")))
