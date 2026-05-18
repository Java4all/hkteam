#!/usr/bin/env bash
# Send a test trace to Langfuse (run on Docker host, executes inside api container).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Langfuse trace smoke test ==="

if ! docker compose ps api --status running 2>/dev/null | grep -q running; then
  echo "ERROR: api container is not running. Run: make start"
  exit 1
fi

echo "--- Langfuse stack ---"
docker compose ps langfuse langfuse-worker clickhouse redis minio 2>/dev/null || true

if ! docker compose ps langfuse --status running 2>/dev/null | grep -q running; then
  echo ""
  echo "ERROR: langfuse container is not running."
  echo "  First boot can take 2–3 minutes: docker compose up -d langfuse"
  echo "  Check logs: docker compose logs langfuse --tail 50"
  exit 1
fi

echo ""
echo "--- DNS from api container (must resolve 'langfuse') ---"
if ! docker compose exec -T api getent hosts langfuse; then
  echo "ERROR: api cannot resolve hostname 'langfuse' — same Docker network?"
  exit 1
fi

echo ""
echo "--- HTTP health from api → langfuse ---"
if ! docker compose exec -T api curl -sf http://langfuse:3000/api/public/health; then
  echo ""
  echo "ERROR: api cannot reach http://langfuse:3000 — wait for langfuse healthy, then retry"
  exit 1
fi
echo ""

echo "--- SDK smoke trace ---"
docker compose exec -T api python -m crisis.observability.test_trace
