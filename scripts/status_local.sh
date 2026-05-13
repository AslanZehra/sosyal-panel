#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

WEB_PID_FILE="$ROOT_DIR/.run/web.pid"
WORKER_PID_FILE="$ROOT_DIR/.run/worker.pid"

check_pid_file() {
  local label="$1"
  local pid_file="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "$label: acik (PID $pid)"
      return
    fi
  fi
  echo "$label: kapali"
}

check_pid_file "Web" "$WEB_PID_FILE"
check_pid_file "Worker" "$WORKER_PID_FILE"
