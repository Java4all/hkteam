# Operations runbook

Install and service layout: [DOCKER.md](DOCKER.md).

## Routine

```bash
make start          # up stack
make health         # API + compose health
make logs           # follow logs
make stop
make restart        # after .env or configs/agents/*.yaml changes
```

## Langfuse v3

Stack uses `langfuse/langfuse:3` + worker + ClickHouse + Redis + MinIO (see [DOCKER.md](DOCKER.md)).

```bash
make test-langfuse          # smoke trace (should appear in UI within ~30s)
curl -s http://127.0.0.1:8080/health | python3 -m json.tool   # langfuse.auth_ok must be true

After each incident in Chainlit, open Langfuse → **Traces** → filter by session id matching `INC-…`.
If `auth_ok` is false, regenerate API keys in the Langfuse project (keys are invalid after DB reset).
```

Keys: project Settings → API Keys → `.env` → `make restart`.

## Checks

| Check | Command / URL |
|-------|----------------|
| API | `curl -s localhost:8080/health` |
| Chainlit | http://localhost:7860 |
| Langfuse | http://localhost:3000 |
| NVIDIA models | `make verify-nvidia-api` |
| Tests (host) | `CRISIS_USE_MOCK_LLM=true make test` |

## Port-forward

```bash
brev port-forward <instance> --port 7860:7860 --port 8080:8080 --port 3000:3000
```

## Docker already installed (Brev)

If `make prerequisites` fails on `containerd.io` conflict: skip reinstall, `cp .env.example .env`, `make start`.
