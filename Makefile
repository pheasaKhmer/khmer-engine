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

# Fails if top-1 accuracy on the bundled sample drops below 85% on the test set (it is
# 88.9%), or below 75% and 80% on the two batches typed by a native speaker (they are
# 78.5% and 86.9%).
eval:
	uv run python eval/evaluate.py --min-top1 0.85
	uv run python eval/evaluate.py --testset eval/native.tsv --min-top1 0.75
	uv run python eval/evaluate.py --testset eval/native2.tsv --min-top1 0.80

data:
	uv run --group data python scripts/build_data.py

sample:
	uv run python scripts/make_sample.py
