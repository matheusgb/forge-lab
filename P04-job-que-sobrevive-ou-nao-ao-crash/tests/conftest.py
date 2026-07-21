from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Client

from lifecycle_api.app import create_app


@pytest.fixture
def event_path(tmp_path: Path) -> Path:
    return tmp_path / "events.jsonl"


@pytest.fixture
def app(event_path: Path) -> FastAPI:
    return create_app(event_path=event_path)


@pytest.fixture
def client(app: FastAPI) -> Generator[Client]:
    with TestClient(app) as test_client:
        yield cast(Client, test_client)
