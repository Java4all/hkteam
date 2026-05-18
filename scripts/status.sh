#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

check() {
  local name="$1" port="$2"
  local pidfile=".pids/${name}.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "[OK] $name PID $(cat "$pidfile") (port $port)"
  elif command -v lsof >/dev/null && lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[OK] $name listening on port $port"
  else
    echo "[--] $name not running (port $port)"
  fi
}

check api 8080
check chainlit 7860
PY="${ROOT}/.venv/bin/python"
if [[ -x "$PY" ]]; then
  curl -sf http://127.0.0.1:8080/health 2>/dev/null | "$PY" -m json.tool 2>/dev/null || echo "Health: API not reachable"
else
  curl -sf http://127.0.0.1:8080/health 2>/dev/null || echo "Health: API not reachable"
fi
