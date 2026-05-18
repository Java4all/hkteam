#!/usr/bin/env bash
# Check or install Ubuntu host prerequisites for Smart City Crisis Management v1.0.
# Usage:
#   ./scripts/prerequisites.sh --check
#   ./scripts/prerequisites.sh --install   # requires sudo
#   make prerequisites
#   make prerequisites-check

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:---check}"
INSTALL_APT_PACKAGES=(
  docker.io
  docker-compose-plugin
  make
  curl
  git
  python3
  python3-venv
  python3-pip
  ca-certificates
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail() { echo -e "${RED}[MISSING]${NC} $*"; FAILED=1; }

FAILED=0

echo "Smart City Crisis Management — prerequisites ($MODE)"
echo "Host: $(uname -s) $(uname -r)"
echo ""

if [[ "$(uname -s)" != "Linux" ]]; then
  warn "This script targets Ubuntu/Linux. On other OS use Docker Desktop or WSL2."
fi

# --- Docker ---
if command -v docker >/dev/null 2>&1; then
  ok "docker ($(docker --version | head -1))"
else
  fail "docker"
fi

if docker compose version >/dev/null 2>&1; then
  ok "docker compose ($(docker compose version --short 2>/dev/null || echo installed))"
elif command -v docker-compose >/dev/null 2>&1; then
  warn "legacy docker-compose found; prefer docker-compose-plugin"
else
  fail "docker compose (plugin)"
fi

# --- CLI tools ---
for cmd in make curl git; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd"
  else
    fail "$cmd"
  fi
done

# --- Python (host pytest / demo optional) ---
if command -v python3 >/dev/null 2>&1; then
  PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  PYMAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
  PYMINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
  if [[ "$PYMAJOR" -gt 3 ]] || [[ "$PYMAJOR" -eq 3 && "$PYMINOR" -ge 11 ]]; then
    ok "python3 $PYVER (>= 3.11)"
  else
    warn "python3 $PYVER — need 3.11+ for host 'make install' / 'make test' (Docker stack does not require host Python)"
  fi
else
  warn "python3 — optional unless you run make install / make test on host"
fi

# --- Docker daemon ---
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "docker daemon running"
  else
    fail "docker daemon not running (try: sudo systemctl start docker)"
  fi
fi

# --- Docker group ---
if id -nG "${USER:-}" 2>/dev/null | grep -qw docker; then
  ok "user in docker group"
else
  warn "user not in docker group — run: sudo usermod -aG docker \$USER && newgrp docker"
fi

# --- .env ---
if [[ -f .env ]]; then
  ok ".env exists"
  if grep -q 'NVIDIA_API_KEY=nvapi-' .env 2>/dev/null || grep -q 'NVIDIA_API_KEY=$' .env 2>/dev/null; then
    warn "NVIDIA_API_KEY not set in .env (use mock: CRISIS_USE_MOCK_LLM=true or set nvapi key)"
  else
    ok "NVIDIA_API_KEY present in .env"
  fi
else
  warn ".env missing — run: cp .env.example .env"
fi

echo ""
if [[ "$MODE" == "--install" ]]; then
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Install mode supports Linux only."
    exit 1
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get not found. Install packages manually — see docs/UBUNTU.md"
    exit 1
  fi
  echo "Installing apt packages (sudo)..."
  sudo apt-get update
  sudo apt-get install -y "${INSTALL_APT_PACKAGES[@]}"
  sudo systemctl enable --now docker 2>/dev/null || true
  if ! id -nG "${USER:-}" 2>/dev/null | grep -qw docker; then
    echo "Adding $USER to docker group..."
    sudo usermod -aG docker "${USER}"
    warn "Log out and back in (or: newgrp docker) for group change"
  fi
  if [[ ! -f .env ]]; then
    cp .env.example .env
    ok "Created .env from .env.example"
  fi
  echo ""
  echo "Install complete. Next: make start"
  FAILED=0
fi

if [[ "$FAILED" -ne 0 && "$MODE" != "--install" ]]; then
  echo ""
  echo "Some requirements missing. Fix with:"
  echo "  make prerequisites        # apt install + docker group"
  echo "  make prerequisites-check    # verify again"
  exit 1
fi

echo ""
echo "Prerequisites OK for Docker workflow."
echo "Next steps:"
echo "  cp .env.example .env   # if needed"
echo "  nano .env              # NVIDIA_API_KEY, Langfuse secrets"
echo "  make start"
