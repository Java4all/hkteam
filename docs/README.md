# Documentation index

| Document | Scope |
|----------|--------|
| [DOCKER.md](DOCKER.md) | **Deploy** — compose services, `.env`, Langfuse v3 keys, troubleshooting |
| [RUNBOOK_v1.md](RUNBOOK_v1.md) | **Operate** — start/stop, health, traces, config reload |
| [UBUNTU.md](UBUNTU.md) | **Host prep** — Docker, prerequisites (before first `make start`) |
| [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) | **Architecture** — pipeline, data models, models table, roadmap |
| [AGENTS.md](AGENTS.md) | **Agents** — YAML workflows, action types, catalog |
| [REQUIREMENTS.md](REQUIREMENTS.md) | **Requirements** — acceptance criteria |
| [diagrams/](diagrams/README.md) | Mermaid diagrams |
| [presentation/PRESENTATION_3_SLIDES.md](presentation/PRESENTATION_3_SLIDES.md) | 5-minute presentation (3 slides) |
| [../data/examples/README.md](../data/examples/README.md) | Example incident text for Chainlit |

## Stack (one line)

**Chainlit** → **API** (LangGraph) → **Postgres** · **Langfuse v3** (UI + worker + ClickHouse + Redis + MinIO) · **NVIDIA cloud LLM**

Diagram: [diagrams/deployment.mmd](diagrams/deployment.mmd)

## Observability

**Langfuse v3** only — images `langfuse/langfuse:3` and `langfuse/langfuse-worker:3` in `docker-compose.yml`. Setup: [DOCKER.md § Langfuse](DOCKER.md#langfuse-api-keys-one-time).

Traces use **LangGraph** (`graph.stream` with Langfuse `CallbackHandler`) — you should see nodes `intake` → `smart_route` → `run_specialists` → `aggregate`, with **BaseChatOpenAI** children for specialist/aggregator LLM calls. Session id = incident id (`INC-…`). Verify: `make test-langfuse` then run an example in Chainlit.
