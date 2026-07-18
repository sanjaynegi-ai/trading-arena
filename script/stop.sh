#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
NAMES=("dashboard" "api" "scheduler")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dashboard-only)
      NAMES=("dashboard")
      ;;
    --api-only)
      NAMES=("api")
      ;;
    --scheduler-only)
      NAMES=("scheduler")
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ! -d "$RUN_DIR" ]]; then
  echo "No .run directory found. Nothing to stop."
  exit 0
fi

for name in "${NAMES[@]}"; do
  pid_file="$RUN_DIR/$name.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not running."
    continue
  fi

  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid"
    fi
    echo "Stopped $name with PID $pid."
  else
    echo "$name process $pid was not running."
  fi

  rm -f "$pid_file"
done
