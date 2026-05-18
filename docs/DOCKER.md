# Docker deployment — v1.0 (mandatory stack)

**Target environment:** NVIDIA GPU cloud instance (Ubuntu 22.04+, e.g. Brev). The full application runs as **Docker Compose** — no bare-metal `uvicorn` for production demos.

LLM inference uses **NVIDIA cloud** from inside the `api` container (`https://integrate.api.nvidia.com/v1` + `NVIDIA_API_KEY`).

## Services

| Service | Port | Role |
|---------|------|------|
| **postgres** | 5432 | Incident DB + Langfuse DB |
| **clickhouse** | — | Langfuse v3 analytics |
| **redis** | — | Langfuse v3 queue |
| **minio** | — | Langfuse v3 object storage |
| **langfuse-worker** | — | Langfuse background worker |
| **langfuse** | 3000 | Trace UI + ingestion API |
| **api** | 8080 | FastAPI + LangGraph + LLM client |
| **chainlit** | 7860 | Operator console |

Diagram: [diagrams/deployment.mmd](diagrams/deployment.mmd)

## Prerequisites (GPU instance host)

```bash
make prerequisites-check   # verify only
make prerequisites         # apt packages + docker group + .env template
```

**Brev / Docker CE:** Docker is often pre-installed. Do **not** run `apt install docker.io` if `containerd.io` is already present — use `make prerequisites-check` and go to `make start` when Docker works.

## First start

```bash
cp .env.example .env
nano .env   # NVIDIA_API_KEY, Langfuse secrets (NEXTAUTH_SECRET, SALT, ENCRYPTION_KEY)

make build      # build smart-city-crisis-app:1.0 locally
make start      # up -d --build
make status
```

The image **`smart-city-crisis-app:1.0` is built from this repo** — not pulled from a registry. If you see `pull access denied`, ensure `docker-compose.yml` has `build: .` on `api` and `chainlit`.

### Access from your laptop

```bash
# Brev
brev port-forward <instance> --port 7860:7860 --port 8080:8080 --port 3000:3000

# SSH
ssh -L 7860:127.0.0.1:7860 -L 8080:127.0.0.1:8080 -L 3000:127.0.0.1:3000 user@gpu-host
```

| URL | Service |
|-----|---------|
| http://localhost:7860 | Chainlit |
| http://localhost:8080/health | API |
| http://localhost:3000 | Langfuse |

Set `CHAINLIT_URL` in `.env` to the URL you use in the browser (e.g. `http://localhost:7860` when port-forwarding).

## Langfuse API keys (one-time)

API keys are **project-scoped** (not under Organization → Settings).

### Option A — UI

1. Open http://localhost:3000
2. Select or create a **project** (sidebar)
3. Project **Settings** → **API Keys**
4. Copy public + secret into `.env` → `make restart`

### Option B — Headless bootstrap (empty DB)

See `.env.example` `LANGFUSE_INIT_*` variables and [RUNBOOK_v1.md](RUNBOOK_v1.md).

```bash
make verify-langfuse-keys
make test-langfuse
```

## Environment essentials

```env
NVIDIA_API_KEY=nvapi-...
LLM_PROFILE=multimodel
NIM_CLOUD_BASE_URL=https://integrate.api.nvidia.com/v1
DATABASE_URL=postgresql://crisis:crisis@postgres:5432/crisis
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
CRISIS_MAX_SUBAGENT_DEPTH=2
SIMULATION_MODE=true
```

Inside Docker, use service hostnames (`postgres`, `langfuse`, `api`) — not `localhost` — in `DATABASE_URL` and `LANGFUSE_HOST`.

## Commands

```bash
make start
make stop
make restart
make logs
make health
make verify-nvidia-api
make clean      # down -v (deletes DB volumes)
```

After code or `public/` UI changes:

```bash
docker compose --env-file .env build api chainlit
docker compose --env-file .env up -d --force-recreate api chainlit
```

## Architecture

```text
[Browser] → chainlit:7860 → api:8080 → postgres
                              ↓
                    NVIDIA cloud (integrate.api.nvidia.com)
                              ↓
                    langfuse:3000 (+ clickhouse, redis, minio)
```

## Host development (optional, not production)

```bash
make install
CRISIS_USE_MOCK_LLM=true make test
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `langfuse` unhealthy but `/api/public/health` OK | `git pull`; recreate langfuse service |
| Langfuse `Region is missing` / S3 errors | `LANGFUSE_S3_*_REGION=auto` in compose; recreate minio + langfuse |
| NVIDIA `[404] Not Found` | Valid `NVIDIA_API_KEY`; enable models on build.nvidia.com; `make verify-nvidia-api` |
| API cannot reach postgres | `DATABASE_URL` host must be `postgres` in Docker |
| Chainlit blank / settings 500 | `make diagnose-chainlit`; rebuild chainlit without cache; check `CHAINLIT_URL` |
| No traces | Langfuse **v3** stack; set project keys; `make test-langfuse` |
| Duplicate review buttons | Hard-refresh browser; ensure latest `public/crisis-ui.js` mounted |

See also [UBUNTU.md](UBUNTU.md) and [TECHNICAL_DESIGN.md §12](TECHNICAL_DESIGN.md).
