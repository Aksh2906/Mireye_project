#!/usr/bin/env bash
set -euo pipefail

MIREYE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MIREYE_ROOT"

MIREYE_FAILED=0

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "[ok] $1: $(command -v "$1")"
  else
    echo "[missing] $1"
    MIREYE_FAILED=1
  fi
}

check_command python3.12
check_command node
check_command npm

if [[ -f .env ]]; then
  echo "[ok] .env exists"
else
  echo "[missing] .env (run: make setup)"
  MIREYE_FAILED=1
fi

if [[ -x .venv/bin/python ]]; then
  if .venv/bin/python -c 'import fastapi, uvicorn, sqlalchemy, httpx, pydantic_settings' >/dev/null 2>&1; then
    echo "[ok] API dependencies"
  else
    echo "[missing] API dependencies (run: make setup)"
    MIREYE_FAILED=1
  fi
else
  echo "[missing] Python virtual environment (run: make setup)"
  MIREYE_FAILED=1
fi

if [[ -d apps/web/node_modules/next ]]; then
  echo "[ok] web dependencies"
else
  echo "[missing] web dependencies (run: make setup)"
  MIREYE_FAILED=1
fi

if [[ "$MIREYE_FAILED" -eq 0 ]]; then
  echo "Local environment is ready. Run: make dev"
else
  echo "Local environment is incomplete. Resolve the items above and rerun: make doctor" >&2
  exit 1
fi

