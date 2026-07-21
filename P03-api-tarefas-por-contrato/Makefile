.PHONY: setup format lint typecheck test check demo experiment openapi run clean

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
	uv run python scripts/demo.py

experiment:
	uv run pytest tests/test_api.py -v

openapi:
	uv run python scripts/export_openapi.py

run:
	uv run uvicorn task_api.main:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache
