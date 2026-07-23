from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lifecycle_api.app import create_app
from lifecycle_api.components import EventJournal, LifecycleFailure, ManagedComponent


def test_lifespan_closes_each_component_once(event_path: Path) -> None:
    journal = EventJournal(event_path)
    client_component = ManagedComponent("client", journal)
    resource_component = ManagedComponent("resource", journal)
    app = create_app(
        event_path=event_path,
        client_factory=lambda: client_component,
        resource_factory=lambda: resource_component,
    )

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.json()["client_active"] is True
        assert response.json()["resource_active"] is True

    assert client_component.close_calls == 1
    assert resource_component.close_calls == 1


def test_startup_failure_closes_component_already_acquired(event_path: Path) -> None:
    journal = EventJournal(event_path)
    client_component = ManagedComponent("client", journal)
    resource_component = ManagedComponent("resource", journal, fail_on_enter=True)
    app = create_app(
        event_path=event_path,
        client_factory=lambda: client_component,
        resource_factory=lambda: resource_component,
    )

    with pytest.raises(LifecycleFailure, match="startup"), TestClient(app):
        pass

    assert client_component.close_calls == 1
    assert resource_component.close_calls == 0


def test_shutdown_failure_does_not_skip_remaining_cleanup(event_path: Path) -> None:
    journal = EventJournal(event_path)
    client_component = ManagedComponent("client", journal)
    resource_component = ManagedComponent("resource", journal, fail_on_close=True)
    app = create_app(
        event_path=event_path,
        client_factory=lambda: client_component,
        resource_factory=lambda: resource_component,
    )

    with pytest.raises(LifecycleFailure, match="shutdown"), TestClient(app):
        pass

    assert client_component.close_calls == 1
    assert resource_component.close_calls == 1
