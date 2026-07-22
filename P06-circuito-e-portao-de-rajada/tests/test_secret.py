import logging

import pytest

from provider_guard.circuit import CircuitBreaker
from provider_guard.client import ProtectedProviderClient
from provider_guard.config import ProviderConfig
from provider_guard.errors import MissingSecretError
from provider_guard.model import CircuitPolicy, ProviderOutcome, TokenBucketPolicy
from provider_guard.provider import FakeProvider
from provider_guard.rate_limit import TokenBucket
from provider_guard.timing import ManualClock


def test_config_loads_secret_from_environment_without_showing_it_in_repr() -> None:
    secret = "secret-that-must-stay-hidden"

    config = ProviderConfig.from_env(
        environ={"CUSTOM_PROVIDER_KEY": secret},
        variable_name="CUSTOM_PROVIDER_KEY",
    )

    assert config.api_key == secret
    assert secret not in repr(config)
    assert "api_key" not in repr(config)


def test_missing_environment_secret_fails_explicitly() -> None:
    with pytest.raises(MissingSecretError, match="P06_PROVIDER_API_KEY"):
        ProviderConfig.from_env(environ={})


def test_secret_never_appears_in_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "log-scan-secret-value"
    clock = ManualClock()
    config = ProviderConfig.from_env(environ={"P06_PROVIDER_API_KEY": secret})
    provider = FakeProvider(
        outcomes=(ProviderOutcome.SUCCESS,),
        expected_api_key=secret,
    )
    client = ProtectedProviderClient(
        config=config,
        provider=provider,
        circuit=CircuitBreaker(policy=CircuitPolicy(), clock=clock),
        bucket=TokenBucket(policy=TokenBucketPolicy(), clock=clock),
    )
    caplog.set_level(logging.INFO)

    client.fetch()

    assert secret not in caplog.text
    assert "provider_request" in caplog.text
    assert "provider_result" in caplog.text
