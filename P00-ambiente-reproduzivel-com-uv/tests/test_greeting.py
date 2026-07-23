import pytest

from p00_ambiente_reproduzivel import greeting


def test_greeting_normalizes_name() -> None:
    assert greeting("  ForgeLab  ") == "Ambiente pronto, ForgeLab!"


def test_greeting_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name cannot be empty"):
        greeting("   ")
