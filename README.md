# Smart City Crisis Management AI

**Version 1.0** — multi-agent decision-support for city emergency operations teams.

**Runtime:** Docker Compose on **Ubuntu** (Postgres + Langfuse + API + Chainlit).

## Documentation

| Document | Description |
|----------|-------------|
| [**Docker deployment**](docs/DOCKER.md) | **Start here** — full stack |
| [Ubuntu setup](docs/UBUNTU.md) | Host prerequisites |
| [Runbook v1.0](docs/RUNBOOK_v1.md) | Operations |
| [Technical Design v1.0](docs/TECHNICAL_DESIGN.md) | Architecture |

## Quick start (Ubuntu + Docker)

```bash
make prerequisites    # first time: apt packages + docker + .env
nano .env             # NVIDIA_API_KEY, Langfuse NEXTAUTH_SECRET / SALT
make start
```

| URL | Service |
|-----|---------|
| http://localhost:7860 | Chainlit (operators) |
| http://localhost:8080/health | API |
| http://localhost:3000 | Langfuse (traces) |

After Langfuse UI is up: create project → add `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` to `.env` → `make restart`.

```bash
make stop
make restart
make logs
make health
```

## Make commands

| Command | Description |
|---------|-------------|
| `make start` | **Docker:** postgres + langfuse + api + chainlit |
| `make stop` | Stop stack |
| `make restart` | Restart stack |
| `make test` | Host pytest (mock LLM, no Docker) |
| `make demo` | Host terminal demo |
| `make clean` | Remove containers **and volumes** |

## Stack (v1.0 mandatory in Docker)

- **PostgreSQL** — incident store  
- **Langfuse** — observability (self-hosted)  
- **API** — FastAPI + LangGraph  
- **Chainlit** — human-in-the-loop UI  
- **NVIDIA cloud** — per-agent LLM (`multimodel` profile)

## Optional: host-only dev

```bash
make install
make test
CRISIS_USE_MOCK_LLM=true make demo
```
