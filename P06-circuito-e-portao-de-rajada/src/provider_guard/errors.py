class ProviderUnavailable(RuntimeError):
    """Falha do provedor que deve ser contada pelo circuito."""


class ProviderAuthenticationError(RuntimeError):
    """Credencial recusada pelo provider fake."""


class CircuitOpenError(RuntimeError):
    def __init__(self, retry_after_seconds: float, *, reason: str = "circuit_open") -> None:
        self.retry_after_seconds = retry_after_seconds
        self.reason = reason
        super().__init__(reason)


class RateLimitExceeded(RuntimeError):
    """A rajada local consumiu todos os tokens disponíveis."""


class MissingSecretError(RuntimeError):
    """A variável de ambiente que guarda o segredo não foi definida."""
