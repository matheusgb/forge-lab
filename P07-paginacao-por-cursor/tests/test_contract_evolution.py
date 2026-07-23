import pytest

from paginated_contract.client import PaginatedClient
from paginated_contract.errors import ContractError
from paginated_contract.feed import ScriptedProvider


def test_v1_consumer_accepts_optional_v2_field() -> None:
    provider = ScriptedProvider(
        {
            None: {
                "items": [
                    {
                        "id": 1,
                        "body": "Campo novo não quebra o consumidor",
                        "created_at": "2026-07-22T12:01:00Z",
                        "author_badge": "top contributor",
                    }
                ],
                "next_cursor": None,
                "api_version": "2",
            }
        }
    )

    result = PaginatedClient(provider).fetch_all()

    assert result.ids == (1,)


def test_renamed_required_field_breaks_the_contract_with_a_clear_error() -> None:
    provider = ScriptedProvider(
        {
            None: {
                "items": [
                    {
                        "id": 1,
                        "text": "body foi renomeado",
                        "created_at": "2026-07-22T12:01:00Z",
                    }
                ],
                "next_cursor": None,
            }
        }
    )

    with pytest.raises(
        ContractError, match=r"response\.items\[0\]\.body: campo obrigatório ausente"
    ):
        PaginatedClient(provider).fetch_all()
