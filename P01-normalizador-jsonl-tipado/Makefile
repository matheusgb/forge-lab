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
	uv run normalize-orders fixtures/orders-mixed.jsonl output/valid.jsonl output/rejected.jsonl

experiment: demo
	uv run pytest tests/test_processor.py::test_output_error_preserves_os_error_as_cause -q
	@echo "--- valid.jsonl"
	@cat output/valid.jsonl
	@echo "--- rejected.jsonl"
	@cat output/rejected.jsonl

clean:
	rm -rf .venv .pytest_cache .ruff_cache output
