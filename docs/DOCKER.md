# Docker deployment

**Environment:** NVIDIA GPU instance, Ubuntu 22.04+, Docker Compose.  
**LLM:** NVIDIA cloud from the `api` container (`NVIDIA_API_KEY`).

## Services

| Service | Port | Role |
|---------|------|------|
| chainlit | 7860 | Operator UI |
| api | 8080 | FastAPI + LangGraph + LLM client |
| postgres | 5432 | Incidents + Langfuse metadata DB |
| langfuse | 3000 | Langfuse **v3** UI + API |
| langfuse-worker | — | Langfuse v3 ingestion |
| clickhouse | — | Langfuse analytics |
| redis | — | Langfuse queue |
| minio | — | Langfuse object storage |

Diagram: [diagrams/deployment.mmd](diagrams/deployment.mmd)

## First deploy

```bash
make prerequisites-check    # or: make prerequisites
cp .env.example .env && nano .env
make build && make start
```

Image `smart-city-crisis-app:1.0` is **built locally** (`build: .` on `api` and `chainlit`).

**Port-forward** (laptop → instance): `7860`, `8080`, `3000`. Set `CHAINLIT_URL=http://localhost:7860` in `.env`.

## Langfuse API keys (one-time)

1. Open http://localhost:3000 → **project** (sidebar) → Settings → **API Keys**
2. Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to `.env`
3. `make restart`

Headless bootstrap: `.env.example` → `LANGFUSE_INIT_*` (fresh DB only).

```bash
make verify-langfuse-keys && make test-langfuse
```

## `.env` (Docker)

Use hostnames `postgres`, `langfuse`, `api` — not `localhost`.

```env
NVIDIA_API_KEY=nvapi-...
LLM_PROFILE=multimodel
DATABASE_URL=postgresql://crisis:crisis@postgres:5432/crisis
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

Full list: `.env.example`.

## Commands

`make start` · `stop` · `restart` · `logs` · `health` · `verify-nvidia-api` · `clean` (removes volumes)

Rebuild UI/API after code changes:

```bash
docker compose --env-file .env build api chainlit
docker compose --env-file .env up -d --force-recreate api chainlit
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No traces after incidents | Keys in `.env` (`pk-lf-` / `sk-lf-`); `curl http://127.0.0.1:8080/health` → `langfuse.auth_ok: true`; `make test-langfuse` (smoke trace); rebuild **api** after code changes. Traces are created per **LLM call** during an incident (`invoke_chat` + `langfuse_incident_session`). Filter UI by session = `INC-…` incident id. |
| Langfuse S3 / Region error | `LANGFUSE_S3_*_REGION=auto`; recreate minio + langfuse |
| NVIDIA 404 / `Function id … version null` | Enable each model on [build.nvidia.com](https://build.nvidia.com/) for your key; `make verify-nvidia-api` lists per-agent probes. Cyber defaults to nemotron-nano (not mistral) in `multimodel.yaml`. |
| Chainlit blank | `CHAINLIT_URL` matches browser; `make diagnose-chainlit`; rebuild chainlit |
| API → DB errors | `DATABASE_URL` host = `postgres` |

Host prep: [UBUNTU.md](UBUNTU.md). Daily ops: [RUNBOOK_v1.md](RUNBOOK_v1.md).
