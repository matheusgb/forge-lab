import json

from fastapi.testclient import TestClient

from tests.conftest import TIMESTAMP, signed_headers
from webhook_inbox.api import AppContainer
from webhook_inbox.model import InboxStatus


def test_response_happens_after_persistence_and_before_effect(
    client: TestClient,
    container: AppContainer,
    authorized_body: bytes,
) -> None:
    response = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body),
    )

    assert response.status_code == 202
    assert response.json() == {
        "event_id": "evt-authorized-1",
        "delivery": "accepted",
        "status": "received",
    }
    assert container.inbox.get("evt-authorized-1").status is InboxStatus.RECEIVED
    assert container.effects.effects == ()


def test_altered_body_fails_the_original_signature(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    altered = authorized_body.replace(b"order-1", b"order-2")

    response = client.post(
        "/webhooks/payments",
        content=altered,
        headers=signed_headers(authorized_body),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "assinatura inválida"}


def test_old_timestamp_is_rejected_even_with_a_valid_signature(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    old_timestamp = TIMESTAMP - 301

    response = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body, old_timestamp),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "timestamp fora da janela aceita"}


def test_future_timestamp_outside_the_window_is_rejected(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    future_timestamp = TIMESTAMP + 301

    response = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body, future_timestamp),
    )

    assert response.status_code == 401


def test_authenticated_malformed_json_returns_422(
    client: TestClient,
) -> None:
    malformed = b"not-json"

    response = client.post(
        "/webhooks/payments",
        content=malformed,
        headers=signed_headers(malformed),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "corpo JSON inválido"}


def test_same_event_and_body_is_acknowledged_as_duplicate(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    first = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body),
    )
    duplicate = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body),
    )

    assert first.status_code == 202
    assert duplicate.status_code == 200
    assert duplicate.json()["delivery"] == "duplicate"


def test_same_event_id_with_other_content_is_a_conflict(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    first = client.post(
        "/webhooks/payments",
        content=authorized_body,
        headers=signed_headers(authorized_body),
    )
    changed_payload = json.loads(authorized_body)
    changed_payload["order_id"] = "order-other"
    changed_body = json.dumps(changed_payload, separators=(",", ":"), sort_keys=True).encode()

    conflict = client.post(
        "/webhooks/payments",
        content=changed_body,
        headers=signed_headers(changed_body),
    )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert "já existe com outro conteúdo" in conflict.json()["detail"]


def test_missing_signature_headers_are_rejected(
    client: TestClient,
    authorized_body: bytes,
) -> None:
    response = client.post("/webhooks/payments", content=authorized_body)

    assert response.status_code == 401
