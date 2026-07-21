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
	mkdir -p output
	uv run run-race --scenario scenario.yaml --output output/results.json

experiment: demo
	@echo "Resultado detalhado salvo em output/results.json"

clean:
	rm -rf .venv .pytest_cache .ruff_cache output
