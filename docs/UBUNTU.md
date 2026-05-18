# GPU instance host setup — Smart City Crisis Management v1.0

Use this guide to prepare an **NVIDIA GPU cloud instance** (Ubuntu 22.04+) before running the **Docker Compose** stack. Production and demos use **`make start` only** — not host-run API/Chainlit.

## 1. System packages

```bash
make prerequisites-check
make prerequisites
```

Installs (when needed): Docker Compose plugin, `make`, `curl`, `git`, Python 3.12 for optional host tests. Creates `.env` from `.env.example`.

**Do not** install `docker.io` on images that already have Docker CE / `containerd.io` (common on Brev) — see [RUNBOOK_v1.md](RUNBOOK_v1.md).

Python **3.11+** is required only for optional host `make install` / `make test`. The Docker stack does not need host Python.

## 2. Clone project

```bash
cd ~/hkteam   # your clone path
cp .env.example .env
nano .env     # NVIDIA_API_KEY=nvapi-...
```

## 3. Start stack (production path)

```bash
make build
make start
make health
```

| Service | URL on instance |
|---------|-----------------|
| Chainlit | http://127.0.0.1:7860 |
| API | http://127.0.0.1:8080/health |
| Langfuse | http://127.0.0.1:3000 |

## 4. Access from your laptop

Port-forward (recommended):

```bash
# Brev
brev port-forward <instance> --port 7860:7860 --port 8080:8080 --port 3000:3000

# SSH
ssh -L 7860:127.0.0.1:7860 -L 8080:127.0.0.1:8080 -L 3000:127.0.0.1:3000 user@your-gpu-host
```

Open http://localhost:7860 on your laptop. Set in `.env`:

```env
CHAINLIT_URL=http://localhost:7860
LANGFUSE_NEXTAUTH_URL=http://localhost:3000
```

## 5. NVIDIA API key

1. Create key at [build.nvidia.com](https://build.nvidia.com/)
2. Set `NVIDIA_API_KEY` in `.env`
3. Enable each model listed in `configs/llm/multimodel.yaml`
4. `make verify-nvidia-api`

## 6. Optional: host tests (no Docker)

```bash
make install
CRISIS_USE_MOCK_LLM=true make test
```

## 7. Optional: local NIM on same GPU host

Not part of default compose. Run a NIM container on port `8000`, then:

```env
NIM_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
```

Reassign agents to `local_llama_8b` in `configs/llm/multimodel.yaml` or use `LLM_PROFILE=local`. The `api` container must reach the host gateway (platform-specific).

## 8. Firewall

Only open ports if you intentionally expose services (use TLS in production):

```bash
sudo ufw allow 7860/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 3000/tcp
```

Prefer SSH/Brev port-forward instead of public exposure.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `make: command not found` | `sudo apt install make` |
| Docker permission denied | `sudo usermod -aG docker $USER` and re-login |
| `containerd.io` conflict | Skip `make prerequisites` docker install; use existing Docker |
| Cloud LLM errors | `NVIDIA_API_KEY`, `make verify-nvidia-api` |

Next: [DOCKER.md](DOCKER.md) · [RUNBOOK_v1.md](RUNBOOK_v1.md)
