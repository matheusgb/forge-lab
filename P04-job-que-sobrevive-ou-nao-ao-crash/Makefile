.PHONY: setup format lint typecheck test check demo experiment run clean

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
	uv run python scripts/run_experiment.py

experiment:
	uv run python scripts/run_experiment.py

run:
	uv run uvicorn lifecycle_api.main:app --reload

clean:
	rm -rf .venv .pytest_cache .ruff_cache output
