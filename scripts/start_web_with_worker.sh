#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Keep worker in same service so queue/archive JSON files stay consistent.
python3 static/worker.py &

exec gunicorn \
  --bind "0.0.0.0:${PORT:-5050}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  main:app
