"""P05: retry seletivo para um provedor instável."""

from retry_client.client import RetryingProviderClient, TimeoutSettings
from retry_client.model import CallReport, Decision, Operation, RetryPolicy
from retry_client.provider import FakeProvider, Outcome

__all__ = [
    "CallReport",
    "Decision",
    "FakeProvider",
    "Operation",
    "Outcome",
    "RetryPolicy",
    "RetryingProviderClient",
    "TimeoutSettings",
]
