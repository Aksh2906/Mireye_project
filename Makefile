.PHONY: dev test lint eval

dev:
	docker compose up --build

test:
	PYTHONPATH=apps/api .venv/bin/pytest -q apps/api/tests

lint:
	.venv/bin/ruff check apps/api/app apps/api/tests evaluation
	PYTHONPATH=apps/api .venv/bin/mypy apps/api/app --ignore-missing-imports
	cd apps/web && npm run lint

eval:
	PYTHONPATH=apps/api .venv/bin/python evaluation/runners/run.py
