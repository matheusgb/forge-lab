import json
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from lifecycle_api.app import CORRELATION_HEADER


def read_events(path: Path) -> list[dict[str, object]]:
    return [cast(dict[str, object], json.loads(line)) for line in path.read_text().splitlines()]


def test_middleware_propagates_received_correlation_id(client: TestClient) -> None:
    response = client.get("/health", headers={CORRELATION_HEADER: "correlation-test"})

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER] == "correlation-test"
    assert response.json()["correlation_id"] == "correlation-test"


def test_middleware_generates_missing_correlation_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER]
    assert response.json()["correlation_id"] == response.headers[CORRELATION_HEADER]


def test_background_task_finishes_during_normal_execution(
    client: TestClient,
    event_path: Path,
) -> None:
    response = client.post("/jobs", json={"duration_seconds": 0.001})

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    events = read_events(event_path)
    job_events = [event["event"] for event in events if event.get("job_id") == job_id]
    assert job_events == ["job_started", "job_completed"]
