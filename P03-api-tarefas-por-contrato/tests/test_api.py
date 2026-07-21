from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Client

from task_api.dependencies import get_repository
from tests.fakes import FailingTaskRepository, FakeTaskRepository

HEADERS = {"X-User-ID": "user-123", "X-Request-ID": "request-123"}


def create_task(client: Client) -> dict[str, object]:
    response = client.post(
        "/tasks",
        headers=HEADERS,
        json={"title": "  Learn FastAPI  ", "description": "  build P03  "},
    )
    assert response.status_code == 201
    return response.json()


def test_create_get_and_complete_task(client: Client) -> None:
    created = create_task(client)
    task_id = str(created["id"])

    found = client.get(f"/tasks/{task_id}", headers=HEADERS)
    completed = client.patch(f"/tasks/{task_id}/complete", headers=HEADERS)

    assert found.status_code == 200
    assert found.json()["title"] == "Learn FastAPI"
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_at"] is not None


def test_invalid_payload_returns_422(client: Client) -> None:
    response = client.post("/tasks", headers=HEADERS, json={"title": "   ", "extra": True})

    assert response.status_code == 422


def test_missing_task_returns_404(client: Client) -> None:
    response = client.get("/tasks/not-found", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "task_not_found"


def test_repeated_transition_returns_409(client: Client) -> None:
    task_id = str(create_task(client)["id"])
    first = client.patch(f"/tasks/{task_id}/complete", headers=HEADERS)
    second = client.patch(f"/tasks/{task_id}/complete", headers=HEADERS)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "task_already_completed"


def test_repository_dependency_can_be_replaced_without_monkeypatch(app: FastAPI) -> None:
    fake = FakeTaskRepository()
    app.dependency_overrides[get_repository] = lambda: fake

    with TestClient(app) as test_client:
        client = cast(Client, test_client)
        created = create_task(client)

    assert str(created["id"]) in fake.tasks


def test_controlled_repository_failure_returns_503(app: FastAPI) -> None:
    app.dependency_overrides[get_repository] = lambda: FailingTaskRepository()

    with TestClient(app) as test_client:
        client = cast(Client, test_client)
        response = client.get("/tasks/any", headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "repository_unavailable"


def test_identity_is_required(client: Client) -> None:
    response = client.get("/tasks/any")

    assert response.status_code == 401
