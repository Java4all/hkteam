# Smart City Crisis Management v1.0
# Primary platform: Ubuntu / Linux (uses scripts/*.sh)
# Windows: uses scripts/*.ps1 when OS=Windows_NT

.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
  PY       ?= .venv/Scripts/python.exe
  PIP      ?= .venv/Scripts/pip.exe
  VENV_BIN := .venv/Scripts
  START    := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start.ps1
  STOP     := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop.ps1
  STATUS   := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/status.ps1
else
  PY       ?= .venv/bin/python
  PIP      ?= .venv/bin/pip
  VENV_BIN := .venv/bin
  START    := ./scripts/start.sh
  STOP     := ./scripts/stop.sh
  STATUS   := ./scripts/status.sh
endif

.PHONY: help install start start-api start-ui start-all stop restart status demo test health clean logs

help: ## Show targets
	@echo Smart City Crisis Management — Make targets
	@echo.
	@echo   make install     Create .venv and install package
	@echo   make start       Start API + Chainlit (background)
	@echo   make start-api   Start API only
	@echo   make start-ui    Start Chainlit only
	@echo   make stop        Stop API and Chainlit
	@echo   make restart     stop then start
	@echo   make status      Show running services
	@echo   make demo        Run 3 terminal demo scenarios
	@echo   make test        Run pytest
	@echo   make health      GET /health
	@echo   make logs        Tail service logs
	@echo   make clean       Remove logs, pids, caches

install: ## pip install -e ".[dev]"
ifeq ($(OS),Windows_NT)
	@if not exist .venv python -m venv .venv
else
	@test -d .venv || python3 -m venv .venv
endif
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	chmod +x scripts/*.sh 2>/dev/null || true

start: ## Start API + Chainlit
	$(START) all

start-api: ## Start FastAPI only
	$(START) api

start-ui: ## Start Chainlit only
	$(START) ui

start-all: start ## Alias for start

stop: ## Stop background services
	$(STOP)

restart: stop ## Restart API + Chainlit
	@$(START) all

status: ## Show PIDs / ports
	$(STATUS)

demo: ## Run scripted demo (cloud if NVIDIA_API_KEY set, else mock)
	$(PY) -m crisis.scripts.run_demo

test: ## pytest
	$(PY) -m pytest tests/ -v

health: ## Curl API health
	@curl -s http://127.0.0.1:8080/health | $(PY) -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8080/health

logs: ## Tail logs/api.log and logs/chainlit.log
	@test -f logs/api.log && tail -f logs/api.log logs/chainlit.log || echo "No logs yet. Run make start first."

clean: ## Remove runtime artifacts
	$(STOP) 2>/dev/null || true
	rm -rf .pids logs/*.log 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
