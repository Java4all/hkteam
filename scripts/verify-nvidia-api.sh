#!/usr/bin/env bash
# Verify NVIDIA_API_KEY and a cloud model from inside the api container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose --env-file .env)

if [ ! -f .env ]; then
  echo "ERROR: No .env — copy .env.example and set NVIDIA_API_KEY=nvapi-..."
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

if [ "${CRISIS_USE_MOCK_LLM:-false}" = "true" ]; then
  echo "OK: CRISIS_USE_MOCK_LLM=true — cloud API check skipped"
  exit 0
fi

KEY="${NVIDIA_API_KEY:-}"
if [ -z "$KEY" ] || [ "$KEY" = "x" ] || [ "$KEY" = "nvapi-..." ]; then
  echo "ERROR: Set NVIDIA_API_KEY=nvapi-... in .env (from https://build.nvidia.com/)"
  exit 1
fi

if ! "${COMPOSE[@]}" ps -q api --status running 2>/dev/null | grep -q .; then
  echo "ERROR: api service not running — run: make start"
  exit 1
fi

echo "=== NVIDIA cloud API check ==="
"${COMPOSE[@]}" exec -T api python -c "
from crisis.llm.nvidia_health import nvidia_health
import json
h = nvidia_health()
print(json.dumps(h, indent=2))
ok = h.get('ok') and h.get('models_ok', True)
if not ok and h.get('models_failed'):
    print('\\nFAILED MODELS — enable on https://build.nvidia.com/ or change configs/llm/multimodel.yaml')
raise SystemExit(0 if ok else 1)
"
