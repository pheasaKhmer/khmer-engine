.PHONY: check lint format test data sample

check: lint test

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

data:
	uv run --group data python scripts/build_data.py

sample:
	uv run python scripts/make_sample.py
