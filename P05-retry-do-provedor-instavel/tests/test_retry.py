from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from retry_client.client import RetryingProviderClient
from retry_client.model import Decision, Operation
from retry_client.provider import FakeProvider, Outcome
from retry_client.timing import RecordingWait

ClientBuilder = Callable[
    [tuple[Outcome, ...]],
    tuple[RetryingProviderClient, FakeProvider, RecordingWait],
]


def test_two_500_then_success_use_deterministic_backoff(
    client_builder: ClientBuilder,
) -> None:
    client, provider, wait = client_builder(
        (Outcome.response(500), Outcome.response(500), Outcome.response(200))
    )

    report = client.call(Operation.SAFE_READ)

    assert provider.attempts == 3
    assert wait.calls == pytest.approx([0.55, 1.1])
    assert [attempt.decision for attempt in report.attempts] == [
        Decision.RETRY_TRANSIENT,
        Decision.RETRY_TRANSIENT,
        Decision.SUCCESS,
    ]


def test_429_respects_retry_after_seconds(client_builder: ClientBuilder) -> None:
    client, provider, wait = client_builder(
        (Outcome.response(429, retry_after="2"), Outcome.response(200))
    )

    report = client.call(Operation.SAFE_READ)

    assert provider.attempts == 2
    assert wait.calls == [2.0]
    assert report.final_decision is Decision.SUCCESS


def test_retry_after_accepts_http_date(client_builder: ClientBuilder) -> None:
    now = datetime(2026, 7, 21, 12, tzinfo=UTC)
    retry_at = format_datetime(now + timedelta(seconds=3), usegmt=True)
    client, _, wait = client_builder(
        (Outcome.response(429, retry_after=retry_at), Outcome.response(200))
    )

    client.call(Operation.SAFE_READ)

    assert wait.calls == [3.0]


def test_timeout_is_retried_for_safe_operation(client_builder: ClientBuilder) -> None:
    client, provider, wait = client_builder((Outcome.timeout(), Outcome.response(200)))

    report = client.call(Operation.SAFE_READ)

    assert provider.attempts == 2
    assert wait.calls == pytest.approx([0.55])
    assert report.final_decision is Decision.SUCCESS


def test_400_is_permanent_and_does_not_wait(client_builder: ClientBuilder) -> None:
    client, provider, wait = client_builder((Outcome.response(400),))

    report = client.call(Operation.SAFE_READ)

    assert provider.attempts == 1
    assert wait.calls == []
    assert report.final_decision is Decision.STOP_PERMANENT


@pytest.mark.parametrize("outcome", [Outcome.response(500), Outcome.timeout()])
def test_unsafe_operation_never_retries(
    client_builder: ClientBuilder,
    outcome: Outcome,
) -> None:
    client, provider, wait = client_builder((outcome, Outcome.response(200)))

    report = client.call(Operation.UNSAFE_CREATE)

    assert provider.attempts == 1
    assert wait.calls == []
    assert report.final_decision is Decision.STOP_UNSAFE


def test_timeout_configuration_separates_connect_and_read(client_builder: ClientBuilder) -> None:
    client, _, _ = client_builder((Outcome.response(200),))

    assert client.http.timeout.connect == 0.2
    assert client.http.timeout.read == 0.5
