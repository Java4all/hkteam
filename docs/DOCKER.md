# Docker deployment — v1.0 (mandatory stack)

v1.0 runs as **Docker Compose** with these **required** services:

| Service | Port | Role |
|---------|------|------|
| **postgres** | 5432 | Incident persistence (JSONB) |
| **langfuse** | 3000 | Observability UI + trace API |
| **api** | 8080 | FastAPI + LangGraph |
| **chainlit** | 7860 | Operator console |

LLM inference still uses **NVIDIA cloud** from inside the `api` container (HTTPS egress).

## Prerequisites (Ubuntu host)

```bash
make prerequisites-check   # verify only
make prerequisites         # apt install + docker group + .env template
```

**Brev / Docker CE images:** Docker is often pre-installed. Do **not** run `apt install docker.io` — it conflicts with `containerd.io`. Use `make prerequisites-check`; if Docker works, go straight to `make start`.

Or manually (only if Docker is missing):

```bash
sudo apt update
sudo apt install -y make curl git python3 python3-venv python3-pip
# only if docker command is missing:
# sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Optional: `export NVIDIA_API_KEY=nvapi-...` in `.env` (not in image).

## First start

```bash
cp .env.example .env
nano .env   # NVIDIA_API_KEY, Langfuse secrets (NEXTAUTH_SECRET, SALT)

make build      # optional: build app image first
make start      # up -d --build (builds smart-city-crisis-app:1.0 locally)
make status
```

The app image **`smart-city-crisis-app:1.0` is built from the repo Dockerfile** — it is not on Docker Hub. If you see `pull access denied for smart-city-crisis-app`, pull the latest `docker-compose.yml` (both `api` and `chainlit` must have `build: .`) and run `make build && make start`.

Open:

- Chainlit: http://\<host\>:7860
- Langfuse: http://\<host\>:3000
- API: http://\<host\>:8080/health

## Langfuse API keys (one-time)

1. Open http://localhost:3000
2. Sign up / create organization and project
3. Settings → API keys → copy public + secret key
4. Add to `.env`:
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   ```
5. `make restart`

Until keys are set, the app runs but tracing is skipped (warning in API logs).

## Commands

```bash
make start      # up -d --build
make stop       # compose down
make restart
make logs
make health
make clean      # down -v (deletes DB volume)
```

## Architecture

```text
[Browser] → chainlit:7860 → api:8080 → postgres
                              ↓
                         NVIDIA cloud LLM
                              ↓
                         langfuse:3000
```

## Host development (optional)

```bash
make install
make test          # mock LLM, no Docker
CRISIS_USE_MOCK_LLM=true make demo
```

Production demo for others: **`make start`** only.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `langfuse` unhealthy | Wait 60s; check `make logs` |
| API cannot reach postgres | `DATABASE_URL` must use host `postgres` inside Docker |
| Chainlit cannot reach API | `API_BASE_URL=http://api:8080` in compose |
| No traces in Langfuse | Set `LANGFUSE_PUBLIC_KEY` / `SECRET_KEY` after project setup |
| `langfuse callback not available` / install langchain | Rebuild API image: `make build --no-cache api` (needs `langchain` package for Langfuse callback) |
| No traces in Langfuse UI | Use **Langfuse v3** stack in compose (not `langfuse:2`); set API keys in `.env`; run `make test-langfuse`; submit incident; check **Traces** (not only Sessions) |
| `auth_ok: false` on `/health` | Regenerate project keys in Langfuse UI; `LANGFUSE_HOST=http://langfuse:3000` inside Docker |
| Port conflict | Change `API_PORT`, `CHAINLIT_PORT`, `LANGFUSE_PORT` in `.env` |
| Chainlit blank page / `project/settings` 500 | Run `make diagnose-chainlit`. Then **`make build` with no cache** and `make restart` (image runs `chainlit init` at build). Ensure `.env` has no bad `CHAINLIT_ROOT_PATH`. Chainlit service no longer loads full `.env`. |
| Chainlit blank (other) | `docker compose logs chainlit`; ensure `CHAINLIT_URL=http://localhost:7860`; unset `CHAINLIT_ROOT_PATH`; hard-refresh browser |
