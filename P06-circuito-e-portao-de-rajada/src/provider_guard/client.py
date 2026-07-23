import logging

from pybreaker import CircuitBreaker

from provider_guard.config import ProviderConfig
from provider_guard.errors import RateLimitExceeded
from provider_guard.provider import Provider
from provider_guard.rate_limit import TokenBucket

logger = logging.getLogger(__name__)


class ProtectedProviderClient:
    def __init__(
        self,
        *,
        config: ProviderConfig,
        provider: Provider,
        circuit: CircuitBreaker,
        bucket: TokenBucket,
    ) -> None:
        self.config = config
        self.provider = provider
        self.circuit = circuit
        self.bucket = bucket

    def fetch(self) -> str:
        return self.circuit.call(self._fetch_with_local_limit)

    def _fetch_with_local_limit(self) -> str:
        if not self.bucket.consume():
            logger.info("rate_limit_rejected endpoint=%s", self.config.endpoint)
            raise RateLimitExceeded("local token bucket is empty")
        logger.info("provider_request endpoint=%s", self.config.endpoint)
        return self.provider.fetch(self.config.api_key.get_secret_value())
