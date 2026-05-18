#!/usr/bin/env bash
# Send a test trace to Langfuse (run on Docker host, executes inside api container).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Match Makefile (same project + .env)
COMPOSE=(docker compose --env-file .env)

compose_service_running() {
  local svc="$1"
  [ -n "$("${COMPOSE[@]}" ps -q "$svc" --status running 2>/dev/null | head -1)" ]
}

echo "=== Langfuse trace smoke test ==="
echo "Project: $(basename "$ROOT") | compose: ${COMPOSE[*]}"
echo ""

if ! compose_service_running api; then
  echo "ERROR: compose service 'api' is not running in this project."
  echo "  From: $ROOT"
  echo "  Run:  make start"
  echo ""
  echo "  Containers on host (for comparison):"
  docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | head -10 || true
  "${COMPOSE[@]}" ps 2>/dev/null || true
  exit 1
fi

echo "--- Langfuse stack ---"
"${COMPOSE[@]}" ps langfuse langfuse-worker clickhouse redis minio 2>/dev/null || true

if ! compose_service_running langfuse; then
  echo ""
  echo "langfuse UI not up yet — starting / waiting (first boot up to ~3 min)..."
  "${COMPOSE[@]}" up -d langfuse 2>/dev/null || true
  for i in $(seq 1 36); do
    if compose_service_running langfuse; then
      echo "langfuse is up (after ${i}0s)"
      break
    fi
    sleep 10
  done
fi

if ! compose_service_running langfuse; then
  echo ""
  echo "ERROR: langfuse UI service is not running (langfuse-worker alone is not enough)."
  echo ""
  echo "Container state:"
  "${COMPOSE[@]}" ps -a langfuse 2>/dev/null || true
  echo ""
  echo "Recent logs:"
  "${COMPOSE[@]}" logs langfuse --tail 40 2>/dev/null || true
  echo ""
  echo "Try: ${COMPOSE[*]} up -d langfuse && ${COMPOSE[*]} logs -f langfuse"
  exit 1
fi

echo ""
echo "--- DNS from api container (must resolve 'langfuse') ---"
if ! "${COMPOSE[@]}" exec -T api getent hosts langfuse; then
  echo "ERROR: api cannot resolve hostname 'langfuse' — same Docker network?"
  exit 1
fi

echo ""
echo "--- HTTP health from api → langfuse ---"
if ! "${COMPOSE[@]}" exec -T api curl -sf http://langfuse:3000/api/public/health; then
  echo ""
  echo "ERROR: api cannot reach http://langfuse:3000 — wait for langfuse healthy, then retry"
  exit 1
fi
echo ""

echo "--- SDK smoke trace ---"
"${COMPOSE[@]}" exec -T api python -m crisis.observability.test_trace
