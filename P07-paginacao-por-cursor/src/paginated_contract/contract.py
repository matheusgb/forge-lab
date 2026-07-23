from pydantic import ValidationError

from paginated_contract.errors import ContractError
from paginated_contract.model import Page


def _format_location(location: tuple[str | int, ...]) -> str:
    path = "response"
    for part in location:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def parse_page(value: object) -> Page:
    try:
        return Page.model_validate(value)
    except ValidationError as error:
        detail = error.errors(include_url=False)[0]
        message = "campo obrigatório ausente" if detail["type"] == "missing" else detail["msg"]
        raise ContractError(f"{_format_location(detail['loc'])}: {message}") from error
