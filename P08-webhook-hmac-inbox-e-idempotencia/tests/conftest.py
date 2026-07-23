import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from webhook_inbox.api import AppContainer, build_container, create_app
from webhook_inbox.signing import sign_payload

SECRET = "controlled-test-secret"
NOW = datetime(2026, 7, 22, 15, 0, tzinfo=UTC)
TIMESTAMP = int(NOW.timestamp())


@pytest.fixture
def container() -> AppContainer:
    return build_container(secret=SECRET, clock=lambda: NOW)


@pytest.fixture
def client(container: AppContainer) -> Iterator[TestClient]:
    with TestClient(create_app(container)) as test_client:
        yield test_client


@pytest.fixture
def authorized_body() -> bytes:
    return json.dumps(
        {
            "event_id": "evt-authorized-1",
            "type": "payment.authorized",
            "order_id": "order-1",
            "occurred_at": "2026-07-22T14:59:30Z",
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def signed_headers(raw_body: bytes, timestamp: int = TIMESTAMP) -> dict[str, str]:
    return {
        "content-type": "application/json",
        "X-Webhook-Timestamp": str(timestamp),
        "X-Webhook-Signature": sign_payload(SECRET, timestamp, raw_body),
    }
