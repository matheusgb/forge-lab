from collections.abc import Mapping
from datetime import datetime
from typing import cast

from paginated_contract.errors import ContractError
from paginated_contract.model import Comment, Page


def _as_object_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ContractError(f"{path}: objeto JSON esperado")

    raw_mapping = cast(dict[object, object], value)
    if any(not isinstance(key, str) for key in raw_mapping):
        raise ContractError(f"{path}: todas as chaves precisam ser texto")
    return cast(dict[str, object], value)


def _required(data: Mapping[str, object], field: str, path: str) -> object:
    if field not in data:
        raise ContractError(f"{path}.{field}: campo obrigatório ausente")
    return data[field]


def _parse_comment(value: object, index: int) -> Comment:
    path = f"items[{index}]"
    data = _as_object_mapping(value, path)
    comment_id = _required(data, "id", path)
    body = _required(data, "body", path)
    created_at = _required(data, "created_at", path)

    if not isinstance(comment_id, int) or isinstance(comment_id, bool):
        raise ContractError(f"{path}.id: número inteiro esperado")
    if not isinstance(body, str) or not body.strip():
        raise ContractError(f"{path}.body: texto não vazio esperado")
    if not isinstance(created_at, str):
        raise ContractError(f"{path}.created_at: data em texto esperada")

    try:
        parsed_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{path}.created_at: data ISO 8601 inválida") from error
    if parsed_date.tzinfo is None:
        raise ContractError(f"{path}.created_at: fuso horário obrigatório")

    return Comment(id=comment_id, body=body, created_at=created_at)


def parse_page(value: object) -> Page:
    data = _as_object_mapping(value, "response")
    raw_items = _required(data, "items", "response")
    raw_cursor = _required(data, "next_cursor", "response")

    if not isinstance(raw_items, list):
        raise ContractError("response.items: lista esperada")
    items_data = cast(list[object], raw_items)

    if raw_cursor is not None and (not isinstance(raw_cursor, str) or not raw_cursor.strip()):
        raise ContractError("response.next_cursor: texto não vazio ou null esperado")

    items = tuple(_parse_comment(item, index) for index, item in enumerate(items_data))
    if not items and raw_cursor is not None:
        raise ContractError("response: página vazia não pode apontar para outra página")
    return Page(items=items, next_cursor=raw_cursor)
