import logging
import secrets
from collections.abc import Sequence
from typing import Protocol

from provider_guard.errors import ProviderAuthenticationError, ProviderUnavailable
from provider_guard.model import ProviderOutcome

logger = logging.getLogger(__name__)


class Provider(Protocol):
    def fetch(self, api_key: str) -> str: ...


class FakeProvider:
    def __init__(
        self,
        *,
        outcomes: Sequence[ProviderOutcome],
        expected_api_key: str,
    ) -> None:
        if not outcomes:
            raise ValueError("fake provider needs at least one outcome")
        self._outcomes = tuple(outcomes)
        self._expected_api_key = expected_api_key
        self._calls = 0

    @property
    def calls(self) -> int:
        return self._calls

    def fetch(self, api_key: str) -> str:
        self._calls += 1
        if not secrets.compare_digest(api_key, self._expected_api_key):
            logger.info("provider_authentication_failed call=%d", self._calls)
            raise ProviderAuthenticationError("provider rejected the configured credential")

        index = self._calls - 1
        if index >= len(self._outcomes):
            raise AssertionError("fake provider received more calls than planned")

        outcome = self._outcomes[index]
        logger.info("provider_result call=%d outcome=%s", self._calls, outcome.value)
        if outcome is ProviderOutcome.FAILURE:
            raise ProviderUnavailable("controlled provider failure")
        return f"resource-{self._calls}"
