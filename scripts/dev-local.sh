#!/usr/bin/env bash
set -euo pipefail

MIREYE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MIREYE_ROOT"

if [[ ! -x .venv/bin/uvicorn || ! -d apps/web/node_modules ]]; then
  echo "Dependencies are missing. Run: make setup" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo ".env is missing. Run: make setup" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///./mireye.sqlite3}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

MIREYE_API_PID=""
MIREYE_WEB_PID=""

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$MIREYE_API_PID" ]]; then kill "$MIREYE_API_PID" 2>/dev/null || true; fi
  if [[ -n "$MIREYE_WEB_PID" ]]; then kill "$MIREYE_WEB_PID" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API at http://localhost:8000"
PYTHONPATH=apps/api .venv/bin/uvicorn app.main:app --reload --reload-dir apps/api --host 127.0.0.1 --port 8000 &
MIREYE_API_PID=$!

echo "Starting web app at http://localhost:3000"
npm --prefix apps/web run dev -- --hostname 127.0.0.1 &
MIREYE_WEB_PID=$!

while kill -0 "$MIREYE_API_PID" 2>/dev/null && kill -0 "$MIREYE_WEB_PID" 2>/dev/null; do
  sleep 1
done

echo "A local service stopped unexpectedly; shutting down the other service." >&2
exit 1
