.PHONY: setup doctor dev api-dev web-dev test lint eval

setup:
	./scripts/setup-local.sh

doctor:
	./scripts/doctor-local.sh

dev:
	./scripts/dev-local.sh

api-dev:
	PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --reload-dir apps/api --host 127.0.0.1 --port 8000

web-dev:
	npm --prefix apps/web run dev -- --hostname 127.0.0.1

test:
	PYTHONPATH=apps/api .venv/bin/pytest -q apps/api/tests

lint:
	.venv/bin/ruff check apps/api/app apps/api/tests evaluation
	PYTHONPATH=apps/api .venv/bin/mypy apps/api/app --ignore-missing-imports
	cd apps/web && npm run lint

eval:
	PYTHONPATH=apps/api .venv/bin/python evaluation/runners/run.py
