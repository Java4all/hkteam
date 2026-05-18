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
# Base packages (never include docker.io here — conflicts with Docker CE / containerd.io on Brev)
BASE_APT_PACKAGES=(
  make
  curl
  git
  python3
  python3-venv
  python3-pip
  ca-certificates
)

docker_ce_installed() {
  dpkg -l containerd.io docker-ce docker-ce-cli 2>/dev/null | grep -q '^ii'
}

compose_available() {
  docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1
}

python_ge_311() {
  local cmd="$1"
  "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

find_preferred_python() {
  local cmd
  for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1 && python_ge_311 "$cmd"; then
      echo "$cmd"
      return 0
    fi
  done
  return 1
}

install_python312() {
  echo "Installing Python 3.12 (sudo)..."
  if sudo apt-get install -y python3.12 python3.12-venv python3.12-dev 2>/dev/null; then
    ok "python3.12 installed from apt"
    return 0
  fi
  warn "python3.12 not in default apt - trying deadsnakes PPA..."
  sudo apt-get install -y software-properties-common
  sudo add-apt-repository -y ppa:deadsnakes/ppa
  sudo apt-get update
  sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
  ok "python3.12 installed from deadsnakes PPA"
}

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

# --- Python 3.11+ (host make install / make test; Docker stack does not need host Python) ---
PREFERRED_PY="$(find_preferred_python || true)"
if [[ -n "$PREFERRED_PY" ]]; then
  PYVER="$("$PREFERRED_PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  ok "$PREFERRED_PY $PYVER - for make install / make test"
else
  if command -v python3 >/dev/null 2>&1; then
    PYVER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    warn "python3 $PYVER - need 3.11+; run: make prerequisites"
  else
    warn "no python3.11+ found - run: make prerequisites"
  fi
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
check_nvidia_api_key() {
  local val
  val="$(grep -E '^[[:space:]]*NVIDIA_API_KEY=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d ' "'\''\r' || true)"
  if [[ -z "$val" ]]; then
    warn "NVIDIA_API_KEY missing from .env"
    return
  fi
  if [[ "$val" == "x" || "$val" == "nvapi-..." ]]; then
    warn "NVIDIA_API_KEY still placeholder in .env - or set CRISIS_USE_MOCK_LLM=true"
    return
  fi
  ok "NVIDIA_API_KEY set in .env"
}

if [[ -f .env ]]; then
  ok ".env exists"
  if grep -qE '^[[:space:]]*CRISIS_USE_MOCK_LLM=[[:space:]]*true' .env 2>/dev/null; then
    ok "CRISIS_USE_MOCK_LLM=true - cloud API key optional"
  else
    check_nvidia_api_key
  fi
else
  warn ".env missing - run: cp .env.example .env"
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
  echo "Installing base apt packages (sudo)..."
  sudo apt-get update
  sudo apt-get install -y "${BASE_APT_PACKAGES[@]}"

  if ! find_preferred_python >/dev/null 2>&1; then
    install_python312
  fi
  PREFERRED_PY="$(find_preferred_python || true)"
  if [[ -n "$PREFERRED_PY" ]]; then
    echo "$PREFERRED_PY" > .preferred-python
    ok "preferred Python: $PREFERRED_PY written to .preferred-python"
  else
    fail "Python 3.11+ still not available after install attempt"
  fi

  if command -v docker >/dev/null 2>&1; then
    ok "Docker already installed — skipping docker.io (avoids containerd.io conflict)"
    if ! compose_available; then
      echo "Installing docker compose plugin only..."
      if ! sudo apt-get install -y docker-compose-plugin 2>/dev/null; then
        warn "Could not install docker-compose-plugin via apt."
        warn "If you use Docker CE, ensure compose v2: docker compose version"
      fi
    fi
  elif docker_ce_installed; then
    warn "Docker CE packages detected but 'docker' not in PATH — try: sudo systemctl start docker"
  else
    echo "Installing docker.io (clean Ubuntu without Docker CE)..."
    sudo apt-get install -y docker.io docker-compose-plugin
  fi

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
