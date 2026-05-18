#!/usr/bin/env bash
# Create .chainlit/config.toml on the host if missing (fixes UI /project/settings 500).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .chainlit/config.toml ]] && grep -q 'generated_by' .chainlit/config.toml 2>/dev/null; then
  echo "OK: .chainlit/config.toml already present"
  grep generated_by .chainlit/config.toml || true
  exit 0
fi

echo "Creating .chainlit via Docker (chainlit init)..."
mkdir -p .chainlit
docker compose build chainlit
docker compose run --rm --no-deps \
  -v "$(pwd)/.chainlit:/app/.chainlit" \
  chainlit \
  sh -c 'rm -f /app/.chainlit/config.toml; python -m chainlit init'

if [[ ! -f .chainlit/config.toml ]]; then
  echo "Failed to create .chainlit/config.toml" >&2
  exit 1
fi

echo "Created:"
grep generated_by .chainlit/config.toml || true
echo "Next: make build && make restart"
