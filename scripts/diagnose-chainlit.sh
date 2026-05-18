#!/usr/bin/env bash
# Diagnose Chainlit /project/settings 500 (blank UI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Chainlit diagnose ==="
echo ""

echo "--- container ---"
docker compose ps chainlit 2>/dev/null || true
echo ""

echo "--- GET /project/settings (must be JSON, not 500) ---"
code="$(curl -sS -o /tmp/cl-settings.json -w "%{http_code}" \
  "http://127.0.0.1:${CHAINLIT_PORT:-7860}/project/settings?language=en-US" || echo "000")"
echo "HTTP $code"
head -c 200 /tmp/cl-settings.json 2>/dev/null || true
echo ""
echo ""

echo "--- config inside running container ---"
docker compose exec -T chainlit sh -c \
  'grep -E "^(name|generated_by)" .chainlit/config.toml 2>/dev/null || echo "NO config.toml"; python -c "from chainlit.config import load_config; load_config(); print(\"load_config: OK\")" 2>&1' \
  || echo "(chainlit container not running)"
echo ""

echo "--- recent logs ---"
docker compose logs chainlit --tail 40 2>/dev/null || true
echo ""
echo "Fix: make build && make restart  (image runs chainlit init at build)"
