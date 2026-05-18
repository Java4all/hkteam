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

.PHONY: help prerequisites prerequisites-check setup install start stop restart status demo test health logs clean build shell-api

help: ## Show targets
	@echo Smart City Crisis Management v1.0 (Docker stack)
	@echo.
	@echo   make prerequisites        Check/install Ubuntu packages (docker, make, curl, ...)
	@echo   make prerequisites-check  Check only, no install
	@echo   make setup                prerequisites + .env + optional host venv
	@echo   make install              Host venv for local pytest/demo (optional)
	@echo   make start                Docker: postgres + langfuse + api + chainlit
	@echo   make stop        Docker compose down
	@echo   make restart     stop + start
	@echo   make status      Container status
	@echo   make build       Build app image only
	@echo   make demo        Host demo script (mock without API key)
	@echo   make test        Host pytest (mock LLM, no Docker required)
	@echo   make health      Curl API /health
	@echo   make logs        Follow compose logs
	@echo   make clean       Down + remove volumes (destructive)

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

restart: stop start ## Restart stack

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
