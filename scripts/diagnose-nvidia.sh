#!/usr/bin/env bash
# Full NVIDIA LLM diagnostic from inside the api container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose --env-file .env)

echo "=== NVIDIA LLM diagnostic ==="
if ! "${COMPOSE[@]}" ps -q api --status running 2>/dev/null | grep -q .; then
  echo "ERROR: api not running"
  exit 1
fi

echo ""
echo "--- .env (redacted) ---"
grep -E '^(NVIDIA_API_KEY|NIM_CLOUD_BASE_URL|LLM_PROFILE|CRISIS_USE_MOCK_LLM)=' .env 2>/dev/null \
  | sed 's/NVIDIA_API_KEY=.*/NVIDIA_API_KEY=***redacted***/' || true

echo ""
echo "--- pip packages ---"
"${COMPOSE[@]}" exec -T api pip show langchain-openai langchain-nvidia-ai-endpoints openai 2>/dev/null \
  | grep -E '^(Name|Version):' || true

echo ""
echo "--- health JSON ---"
"${COMPOSE[@]}" exec -T api python -c "
import json
from crisis.llm.nvidia_health import nvidia_health
print(json.dumps(nvidia_health(), indent=2))
"
