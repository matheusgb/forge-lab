"""Contrato HTTP paginado e feed mutável para o P07."""

from paginated_contract.client import OffsetPaginatedClient, PaginatedClient
from paginated_contract.errors import ContractError, CursorLoopError, InvalidCursorError
from paginated_contract.feed import MutableCommentFeed, ScriptedProvider
from paginated_contract.model import Comment, Page, WalkResult

__all__ = [
    "Comment",
    "ContractError",
    "CursorLoopError",
    "InvalidCursorError",
    "MutableCommentFeed",
    "OffsetPaginatedClient",
    "Page",
    "PaginatedClient",
    "ScriptedProvider",
    "WalkResult",
]
