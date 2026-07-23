from pybreaker import CircuitBreakerError


class ProviderUnavailable(RuntimeError):
    """Falha do provedor que deve ser contada pelo circuito."""


class ProviderAuthenticationError(RuntimeError):
    """Credencial recusada pelo provider fake."""


CircuitOpenError = CircuitBreakerError


class RateLimitExceeded(RuntimeError):
    """A rajada local consumiu todos os tokens disponíveis."""
