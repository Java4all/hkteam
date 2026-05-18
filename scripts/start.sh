#!/usr/bin/env bash
# Start crisis API and/or Chainlit in background (Ubuntu / Linux).
# Usage: ./scripts/start.sh [api|ui|all]

set -euo pipefail
export PYTHONUNBUFFERED=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
TARGET="${1:-all}"

mkdir -p .pids logs

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Run: make install"; exit 1; }

start_one() {
  local name="$1"
  shift
  local pidfile=".pids/${name}.pid"
  local logfile="logs/${name}.log"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running (PID $(cat "$pidfile"))"
    return
  fi
  nohup "$@" >>"$logfile" 2>&1 &
  echo $! >"$pidfile"
  echo "Started $name PID $(cat "$pidfile") -> $logfile"
}

case "$TARGET" in
  api)
    start_one api "$PY" -m uvicorn crisis.api.main:app --host 127.0.0.1 --port 8080
    ;;
  ui)
    start_one chainlit "$PY" -m chainlit run src/crisis/ui/chainlit_app.py --port 7860 --host 127.0.0.1
    ;;
  all|*)
    start_one api "$PY" -m uvicorn crisis.api.main:app --host 127.0.0.1 --port 8080
    sleep 2
    start_one chainlit "$PY" -m chainlit run src/crisis/ui/chainlit_app.py --port 7860 --host 127.0.0.1
    ;;
esac

echo ""
echo "API:      http://127.0.0.1:8080/health"
echo "Chainlit: http://127.0.0.1:7860"
echo "Stop:     make stop"
