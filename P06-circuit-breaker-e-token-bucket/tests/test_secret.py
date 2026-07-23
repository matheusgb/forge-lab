import logging

import pytest
from pydantic import ValidationError

from provider_guard.circuit import build_circuit
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.model import CircuitPolicy, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket


def test_settings_load_secret_from_environment_without_showing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "secret-that-must-stay-hidden"
    monkeypatch.setenv("P06_PROVIDER_API_KEY", secret)

    config = ProviderConfig()  # pyright: ignore[reportCallIssue]

    assert config.api_key.get_secret_value() == secret
    assert secret not in repr(config)


def test_missing_secret_fails_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("P06_PROVIDER_API_KEY", raising=False)

    with pytest.raises(ValidationError, match="api_key"):
        ProviderConfig()  # pyright: ignore[reportCallIssue]


def test_secret_never_appears_in_logs(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "log-scan-secret-value"
    monkeypatch.setenv("P06_PROVIDER_API_KEY", secret)
    config = ProviderConfig()  # pyright: ignore[reportCallIssue]
    provider = FakeProvider(outcomes=(ProviderOutcome.SUCCESS,), expected_api_key=secret)
    client = ProtectedProviderClient(
        config=config,
        provider=provider,
        circuit=build_circuit(CircuitPolicy()),
        bucket=TokenBucket(policy=TokenBucketPolicy()),
    )
    caplog.set_level(logging.INFO)

    client.fetch()

    assert secret not in caplog.text
    assert "provider_request" in caplog.text
