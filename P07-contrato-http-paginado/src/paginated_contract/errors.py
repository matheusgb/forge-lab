class PaginationError(ValueError):
    """Erro conhecido durante o consumo das páginas."""


class ContractError(PaginationError):
    """A resposta não respeita o contrato esperado pelo consumidor."""


class CursorLoopError(PaginationError):
    """O provider devolveu um cursor que já foi percorrido."""


class InvalidCursorError(PaginationError):
    """O cursor não pode ser interpretado pelo provider."""
