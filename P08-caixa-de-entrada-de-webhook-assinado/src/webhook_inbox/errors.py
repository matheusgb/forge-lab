class WebhookError(ValueError):
    """Erro conhecido no recebimento ou processamento do webhook."""


class InvalidSignatureError(WebhookError):
    """A assinatura não corresponde ao timestamp e corpo recebidos."""


class ReplayRejectedError(WebhookError):
    """O timestamp está fora da janela aceita."""


class InvalidPayloadError(WebhookError):
    """O corpo autenticado não respeita o contrato sintético."""


class DuplicateEventConflictError(WebhookError):
    """O mesmo event_id chegou com outro conteúdo."""


class EventNotFoundError(WebhookError):
    """O worker recebeu um ID que não existe na inbox."""


class OutOfOrderEventError(WebhookError):
    """O evento depende de outro efeito que ainda não aconteceu."""


class SimulatedCrash(RuntimeError):
    """Interrupção controlada usada pelo experimento."""
