# GPU host prerequisites

Prepare the instance before [DOCKER.md](DOCKER.md) deploy.

```bash
make prerequisites-check
make prerequisites    # Docker, make, .env template — skip if Docker CE already present
cp .env.example .env
nano .env             # NVIDIA_API_KEY minimum
```

| Situation | Action |
|-----------|--------|
| Docker works (`docker compose version`) | Go to `make start` in [DOCKER.md](DOCKER.md) |
| `containerd.io` apt conflict | Docker pre-installed — do not install `docker.io` |
| Host tests only | `make install` + `CRISIS_USE_MOCK_LLM=true make test` |

Port-forward and Langfuse setup: [DOCKER.md](DOCKER.md). Operations: [RUNBOOK_v1.md](RUNBOOK_v1.md).
