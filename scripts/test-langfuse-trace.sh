#!/usr/bin/env bash
# Send a test trace to Langfuse and verify auth (run on the Docker host).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env — cp .env.example .env and set LANGFUSE_* keys"
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

echo "=== Langfuse trace smoke test ==="
docker compose exec -T api python - <<'PY'
import os
from langfuse import get_client

pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
host = os.environ.get("LANGFUSE_BASE_URL") or os.environ.get("LANGFUSE_HOST", "")
print("host:", host)
print("public_key set:", bool(pk))

client = get_client(public_key=pk)
print("auth_check:", client.auth_check())
with client.start_as_current_span(name="smoke-test") as span:
    span.update(input={"hello": "world"}, output={"status": "ok"})
client.flush()
print("flush done — open Langfuse UI → Traces and look for smoke-test")
PY
