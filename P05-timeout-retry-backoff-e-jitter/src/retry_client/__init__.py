"""P05: retry seletivo para um provedor instável."""

from retry_client.client import RetryingProviderClient
from retry_client.model import CallResult, Decision, Operation, RetryPolicy
from retry_client.provider import FakeProvider, Outcome

__all__ = [
    "CallResult",
    "Decision",
    "FakeProvider",
    "Operation",
    "Outcome",
    "RetryPolicy",
    "RetryingProviderClient",
]
