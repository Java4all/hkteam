# Runbook — Smart City Crisis Management v1.0

**Primary:** [DOCKER.md](DOCKER.md) — `make start`

## Prerequisites (Ubuntu)

```bash
make prerequisites-check
make prerequisites         # installs packages (sudo), creates .env
```

On Ubuntu 22.04, default `python3` is often 3.10. `make prerequisites` installs **Python 3.12 only if** no 3.11+ is found (optional for host `make install` / `make test`). The Docker stack does not require host Python.

## Start / stop

```bash
cp .env.example .env
nano .env
make build      # first time: build app image locally
make start
make status
make health
make logs
make stop
make restart
```

## Langfuse keys (required for tracing)

1. http://localhost:3000 → create account & project  
2. Copy API keys into `.env`  
3. `make restart`

## Environment essentials

```env
NVIDIA_API_KEY=nvapi-...
DATABASE_URL=postgresql://crisis:crisis@postgres:5432/crisis
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://langfuse:3000
LANGFUSE_NEXTAUTH_SECRET=...   # min 32 chars
LANGFUSE_SALT=...              # min 32 chars
```

## Host tests (no Docker)

```bash
make install
make test
```

## SSH port forward

```bash
ssh -L 8080:127.0.0.1:8080 -L 7860:127.0.0.1:7860 -L 3000:127.0.0.1:3000 user@gpu-host
```

Or with Brev (from your laptop):

```bash
brev port-forward <instance> --port 7860:7860 --port 8080:8080 --port 3000:3000
```

## `containerd.io` / `docker.io` conflict (Brev / Docker CE)

If `make prerequisites` fails with `containerd.io Conflicts: containerd`, Docker is **already installed** (common on Brev). Skip reinstall:

```bash
docker --version
docker compose version
make prerequisites-check
```

If checks pass, only run:

```bash
cp .env.example .env
make start
```

Re-run `make prerequisites` after updating the repo — it no longer installs `docker.io` when Docker is present.
