# Smart City Crisis Management v1.0 — Docker-first (Ubuntu / Linux)
# Primary: make start  →  docker compose up (postgres + langfuse + api + chainlit)

.DEFAULT_GOAL := help
COMPOSE := docker compose --env-file .env

ifeq ($(OS),Windows_NT)
  PY       ?= .venv/Scripts/python.exe
  PIP      ?= .venv/Scripts/pip.exe
  PYTHON_CMD ?= python
else
  PYTHON_CMD ?= $(shell if [ -f .preferred-python ]; then cat .preferred-python; elif command -v python3.12 >/dev/null 2>&1; then echo python3.12; else echo python3; fi)
  PY       ?= .venv/bin/python
  PIP      ?= .venv/bin/pip
endif

.PHONY: help prerequisites prerequisites-check setup install build chainlit-init bootstrap-chainlit diagnose-chainlit start stop restart status demo test health logs clean shell-api

help: ## Show all make targets (default)
	@echo Smart City Crisis Management v1.0 — Docker stack
	@echo.
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9][a-zA-Z0-9_-]*:.*## / {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@echo.
	@echo URLs after make start:
	@echo "  Chainlit  http://127.0.0.1:7860"
	@echo "  API       http://127.0.0.1:8080/health"
	@echo "  Langfuse  http://127.0.0.1:3000"

ifeq ($(OS),Windows_NT)
prerequisites-check prerequisites:
	@echo prerequisites targets require Ubuntu/Linux or WSL2.
	@echo Run: bash scripts/prerequisites.sh --check
	@exit 1

setup:
	@echo On Windows use WSL2, then: make prerequisites && make start
	@exit 1
else
prerequisites-check: ## Check host prerequisites (no sudo)
	chmod +x scripts/prerequisites.sh
	bash scripts/prerequisites.sh --check

prerequisites: ## Install/check Ubuntu prerequisites (uses sudo)
	chmod +x scripts/prerequisites.sh
	bash scripts/prerequisites.sh --install

setup: prerequisites ## Full first-time setup: apt + .env
	@test -f .env || cp .env.example .env
	@echo ""
	@echo "Setup done. Edit .env then: make start"
endif

install: ## Local venv for pytest (optional; uses python3.12 if available)
ifeq ($(OS),Windows_NT)
	@if not exist .venv python -m venv .venv
else
	@test -d .venv || $(PYTHON_CMD) -m venv .venv
	@.venv/bin/python --version
endif
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"

build: ## Build Docker images
	$(COMPOSE) build

chainlit-init: ## Regenerate .chainlit/config.toml on host (needs: make install)
	$(PYTHON_CMD) -m chainlit init

bootstrap-chainlit: ## Create .chainlit on host via Docker if missing
	chmod +x scripts/bootstrap-chainlit.sh
	bash scripts/bootstrap-chainlit.sh

diagnose-chainlit: ## Debug Chainlit blank UI / project/settings 500
	chmod +x scripts/diagnose-chainlit.sh
	bash scripts/diagnose-chainlit.sh

langfuse-keys-help: ## Print where API keys live in Langfuse v3 UI
	@echo "Langfuse API keys are per PROJECT, not under Organization settings."
	@echo ""
	@echo "  1. Open http://localhost:3000"
	@echo "  2. Sidebar: click a project (or '+ New project')"
	@echo "  3. Project → Settings → API Keys"
	@echo ""
	@echo "Wrong URL (no API keys): /organization/.../settings"
	@echo "Optional: LANGFUSE_INIT_* in .env — see .env.example and docs/DOCKER.md"

verify-nvidia-api: ## Test NVIDIA_API_KEY + cloud model from api container
	chmod +x scripts/verify-nvidia-api.sh
	bash scripts/verify-nvidia-api.sh

verify-langfuse-keys: ## HTTP check that .env pk/sk match running Langfuse
	chmod +x scripts/verify-langfuse-keys.sh
	bash scripts/verify-langfuse-keys.sh

test-langfuse: ## Send smoke trace to Langfuse (verify keys + SDK)
	chmod +x scripts/test-langfuse-trace.sh
	bash scripts/test-langfuse-trace.sh

start: ## Start full stack (Docker)
	@test -f .env || (echo "Copy .env.example to .env first" && exit 1)
	$(COMPOSE) up -d --build
	@echo ""
	@echo "API:       http://127.0.0.1:8080/health"
	@echo "Chainlit:  http://127.0.0.1:7860"
	@echo "Langfuse:  http://127.0.0.1:3000"
	@echo ""
	@echo "Create Langfuse project → copy keys to .env → make restart"

stop: ## Stop Docker stack
	$(COMPOSE) down

restart: stop start ## Restart Docker stack (stop + start)

status: ## Docker compose ps
	$(COMPOSE) ps

demo: ## Terminal demo on host (set CRISIS_USE_MOCK_LLM=true without API key)
	$(PY) -m crisis.scripts.run_demo

test: ## pytest on host (no Docker)
	CRISIS_USE_MOCK_LLM=true $(PY) -m pytest tests/ -v

health: ## API health check
	@curl -sf http://127.0.0.1:8080/health | $(PY) -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8080/health

logs: ## Follow all service logs
	$(COMPOSE) logs -f --tail=100

clean: ## Stop and remove volumes
	$(COMPOSE) down -v
	rm -rf .pids logs/*.log 2>/dev/null || true

shell-api: ## Shell inside api container
	$(COMPOSE) exec api bash
