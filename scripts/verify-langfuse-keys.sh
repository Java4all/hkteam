#!/usr/bin/env bash
# Verify LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY against the running Langfuse instance.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "ERROR: No .env — copy .env.example and set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY"
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

PK="${LANGFUSE_PUBLIC_KEY:-}"
SK="${LANGFUSE_SECRET_KEY:-}"
HOST="${LANGFUSE_HOST:-http://langfuse:3000}"

if [ -z "$PK" ] || [ -z "$SK" ]; then
  echo "ERROR: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set in .env"
  exit 1
fi

case "$PK" in pk-lf-*) ;; *)
  echo "WARN: LANGFUSE_PUBLIC_KEY should start with pk-lf- (copy from Langfuse UI)"
  ;;
esac
case "$SK" in sk-lf-*) ;; *)
  echo "WARN: LANGFUSE_SECRET_KEY should start with sk-lf- (copy from Langfuse UI)"
  ;;
esac

echo "=== Langfuse API key check ==="
echo "Host (from .env): $HOST"
echo "Public key: ${PK:0:16}..."

COMPOSE=(docker compose --env-file .env)
if ! "${COMPOSE[@]}" ps -q api --status running 2>/dev/null | grep -q .; then
  echo "ERROR: api service not running — run: make start"
  exit 1
fi

# Basic auth against a protected public route (401 = bad keys, 200 = OK)
HTTP_CODE=$("${COMPOSE[@]}" exec -T api curl -s -o /tmp/langfuse-projects.json -w "%{http_code}" \
  -u "${PK}:${SK}" "http://langfuse:3000/api/public/projects" || echo "000")

echo "GET /api/public/projects → HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo "OK: API keys match this Langfuse instance."
  head -c 200 /tmp/langfuse-projects.json 2>/dev/null || true
  echo ""
  exit 0
fi

echo ""
echo "ERROR: Keys rejected (expected HTTP 200, got $HTTP_CODE)."
echo "  Regenerate keys in Langfuse UI → project Settings → API Keys"
echo "  Update .env with the new pk-lf- and sk-lf- pair, then: make restart"
exit 1
