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
# 88.1%), or below 70% and 65% on the two batches typed by a native speaker (they are
# 76.9% and 68.3%).
eval:
	uv run python eval/evaluate.py --min-top1 0.85
	uv run python eval/evaluate.py --testset eval/native.tsv --min-top1 0.70
	uv run python eval/evaluate.py --testset eval/native2.tsv --min-top1 0.65

data:
	uv run --group data python scripts/build_data.py

sample:
	uv run python scripts/make_sample.py
