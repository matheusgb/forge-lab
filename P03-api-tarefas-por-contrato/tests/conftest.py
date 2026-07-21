from collections.abc import Generator
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Client

from task_api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Generator[Client]:
    with TestClient(app) as test_client:
        yield cast(Client, test_client)
