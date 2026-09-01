#!/usr/bin/env bash
set -euo pipefail

MIREYE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MIREYE_ROOT"

if command -v python3.12 >/dev/null 2>&1; then
  MIREYE_PYTHON_BIN="$(command -v python3.12)"
else
  echo "Python 3.12 is required. Install it and rerun this command." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required. Install Node.js 22+ and rerun this command." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  touch .env
  chmod 600 .env
  echo "Created a private .env file. Add provider credentials from the README when available."
fi

if [[ ! -x .venv/bin/python ]]; then
  "$MIREYE_PYTHON_BIN" -m venv .venv
fi

.venv/bin/pip install -r apps/api/requirements-local.txt
npm install --prefix apps/web

echo
./scripts/doctor-local.sh
