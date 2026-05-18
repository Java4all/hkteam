# Ubuntu setup — Smart City Crisis Management v1.0

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip make curl git
```

Python **3.11+** is required. Check:

```bash
python3 --version
```

On Ubuntu 22.04, if needed:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv
# then use python3.11 -m venv .venv
```

## 2. Clone / enter project

```bash
cd ~/hkteam   # your clone path
```

## 3. Install application

```bash
make install
cp .env.example .env
nano .env     # set NVIDIA_API_KEY=nvapi-...
```

## 4. Run

```bash
make demo      # quick terminal demo (uses cloud if key set)
make start     # API http://127.0.0.1:8080 + Chainlit http://127.0.0.1:7860
make status
make health
make logs      # Ctrl+C to exit tail
make stop
make restart
```

## 5. Open from another machine (GPU cloud instance)

If the app binds to `127.0.0.1` only, use SSH port forwarding:

```bash
ssh -L 8080:127.0.0.1:8080 -L 7860:127.0.0.1:7860 user@your-gpu-host
```

Then open `http://127.0.0.1:7860` on your laptop.

To listen on all interfaces (lab only), change start scripts or run manually:

```bash
.venv/bin/python -m uvicorn crisis.api.main:app --host 0.0.0.0 --port 8080
```

## 6. Offline demo (no NVIDIA API key)

```bash
export CRISIS_USE_MOCK_LLM=true
make demo
make test
```

## 7. Optional: local NIM on the same Ubuntu GPU host

Run NVIDIA NIM container on port `8000`, then in `configs/llm/multimodel.yaml` assign agents to `local_llama_8b` and set in `.env`:

```env
NIM_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
```

## 8. Optional: Langfuse (Docker)

```bash
# follow Langfuse self-host docs, then in .env:
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://127.0.0.1:3000
make restart
```

## 9. Firewall (if enabled)

```bash
sudo ufw allow 8080/tcp   # only if exposing API publicly (not recommended without TLS)
sudo ufw allow 7860/tcp
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `make: command not found` | `sudo apt install make` |
| `venv` fails | `sudo apt install python3-venv` |
| Port in use | `make stop` or `sudo lsof -i :8080` |
| Cloud LLM errors | Check `NVIDIA_API_KEY` in `.env`, model IDs in `configs/llm/multimodel.yaml` |
| Chainlit cannot reach API | `API_BASE_URL=http://127.0.0.1:8080` in `.env` |
