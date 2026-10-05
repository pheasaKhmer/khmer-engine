.PHONY: check lint format test eval data sample

check: lint test eval

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

# Fails if top-1 accuracy on the bundled sample drops below 85% (it is 86.5%).
eval:
	uv run python eval/evaluate.py --min-top1 0.85

data:
	uv run --group data python scripts/build_data.py

sample:
	uv run python scripts/make_sample.py
