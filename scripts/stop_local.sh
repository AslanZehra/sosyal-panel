#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

WEB_PID_FILE="$ROOT_DIR/.run/web.pid"
WORKER_PID_FILE="$ROOT_DIR/.run/worker.pid"

stop_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
    fi
    rm -f "$pid_file"
  fi
}

stop_pid_file "$WEB_PID_FILE"
stop_pid_file "$WORKER_PID_FILE"

echo "Local web ve worker durduruldu."
