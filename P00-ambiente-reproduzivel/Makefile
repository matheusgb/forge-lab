.PHONY: setup format lint typecheck test check demo experiment clean

setup:
	uv sync --locked

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run pyright

test:
	uv run pytest

check: lint typecheck test

demo:
	uv run p00 ForgeLab

experiment:
	uv run python scripts/verify_failures.py

clean:
	rm -rf .venv .pytest_cache .ruff_cache
