#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p .run

WEB_LOG="$ROOT_DIR/.run/web.log"
WORKER_LOG="$ROOT_DIR/.run/worker.log"
WEB_PID_FILE="$ROOT_DIR/.run/web.pid"
WORKER_PID_FILE="$ROOT_DIR/.run/worker.pid"

if [[ ! -x "$ROOT_DIR/venv/bin/python3" ]]; then
  echo "venv/bin/python3 bulunamadi."
  exit 1
fi

if [[ -f "$WEB_PID_FILE" ]] && kill -0 "$(cat "$WEB_PID_FILE")" 2>/dev/null; then
  echo "Web zaten acik. PID: $(cat "$WEB_PID_FILE")"
else
  nohup "$ROOT_DIR/venv/bin/python3" main.py >"$WEB_LOG" 2>&1 &
  echo $! > "$WEB_PID_FILE"
  sleep 1
fi

if [[ -f "$WORKER_PID_FILE" ]] && kill -0 "$(cat "$WORKER_PID_FILE")" 2>/dev/null; then
  echo "Worker zaten acik. PID: $(cat "$WORKER_PID_FILE")"
else
  nohup "$ROOT_DIR/venv/bin/python3" static/worker.py >"$WORKER_LOG" 2>&1 &
  echo $! > "$WORKER_PID_FILE"
  sleep 1
fi

WEB_PID="$(cat "$WEB_PID_FILE" 2>/dev/null || true)"
WORKER_PID="$(cat "$WORKER_PID_FILE" 2>/dev/null || true)"

if [[ -n "$WEB_PID" ]] && kill -0 "$WEB_PID" 2>/dev/null; then
  echo "Web acik: PID $WEB_PID"
else
  echo "Web baslatilamadi. Log: $WEB_LOG"
fi

if [[ -n "$WORKER_PID" ]] && kill -0 "$WORKER_PID" 2>/dev/null; then
  echo "Worker acik: PID $WORKER_PID"
else
  echo "Worker baslatilamadi. Log: $WORKER_LOG"
fi

echo "Panel: http://127.0.0.1:5050"
echo "Web log: $WEB_LOG"
echo "Worker log: $WORKER_LOG"
