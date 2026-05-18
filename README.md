# Smart City Crisis Management AI

**v1.0** — multi-agent crisis decision-support for city emergency operations.

Runs on an **NVIDIA GPU instance** as **Docker Compose**. LLM inference uses **NVIDIA cloud** (`integrate.api.nvidia.com`).

## Quick start

```bash
cp .env.example .env && nano .env   # NVIDIA_API_KEY, Langfuse secrets
make prerequisites                  # first time
make start
```

Port-forward from your laptop: `7860` Chainlit · `8080` API · `3000` Langfuse.

```bash
brev port-forward <instance> --port 7860:7860 --port 8080:8080 --port 3000:3000
```

After first start: Langfuse → project → **API Keys** → add to `.env` → `make restart`.

| URL | Service |
|-----|---------|
| http://localhost:7860 | Operator UI (Chainlit) |
| http://localhost:8080/health/live | API liveness |
| http://localhost:8080/health | API diagnostics (add `?deep=1` for NVIDIA) |
| http://localhost:3000 | Langfuse traces |

## Documentation

| Doc | Use for |
|-----|---------|
| [**docs/README.md**](docs/README.md) | **Index** — what to read when |
| [docs/DOCKER.md](docs/DOCKER.md) | Deploy, services, Langfuse keys, troubleshooting |
| [docs/RUNBOOK_v1.md](docs/RUNBOOK_v1.md) | Start/stop, health, daily ops |
| [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md) | Architecture, models, security |
| [docs/AGENTS.md](docs/AGENTS.md) | Per-agent YAML workflows |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Product requirements (Req 1–15) |
| [Presentation (3 slides)](docs/presentation/PRESENTATION_3_SLIDES.md) | 5-minute overview deck |
