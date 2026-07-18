#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
DASHBOARD_PORT="${DASHBOARD_PORT:-7860}"
API_PORT="${API_PORT:-8000}"
START_DASHBOARD=1
START_API=1
START_SCHEDULER=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-dashboard)
      START_DASHBOARD=0
      ;;
    --no-api)
      START_API=0
      ;;
    --no-scheduler)
      START_SCHEDULER=0
      ;;
    --dashboard-port)
      DASHBOARD_PORT="$2"
      shift
      ;;
    --api-port)
      API_PORT="$2"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

mkdir -p "$RUN_DIR"

is_running() {
  local name="$1"
  local pid_file="$RUN_DIR/$name.pid"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

start_process() {
  local name="$1"
  shift

  if is_running "$name"; then
    echo "$name is already running."
    return
  fi

  (
    cd "$PROJECT_ROOT"
    nohup "$@" >"$RUN_DIR/$name.out.log" 2>"$RUN_DIR/$name.err.log" &
    echo $! >"$RUN_DIR/$name.pid"
  )

  echo "Started $name with PID $(cat "$RUN_DIR/$name.pid")."
}

if [[ "$START_DASHBOARD" -eq 1 ]]; then
  start_process dashboard uv run python app.py --server-port "$DASHBOARD_PORT"
fi

if [[ "$START_API" -eq 1 ]]; then
  start_process api uv run uvicorn backend.api:app --port "$API_PORT"
fi

if [[ "$START_SCHEDULER" -eq 1 ]]; then
  start_process scheduler uv run -m backend.trading_arena
fi

echo
echo "Dashboard: http://127.0.0.1:$DASHBOARD_PORT"
echo "API:       http://127.0.0.1:$API_PORT"
echo "Logs:      $RUN_DIR"
echo
echo "Stop with: ./script/stop.sh"
