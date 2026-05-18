# Runbook — Smart City Crisis Management v1.0 (Ubuntu)

See also: [UBUNTU.md](UBUNTU.md) for full setup and troubleshooting.

## Prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-venv make curl
```

## One-command workflow (Make)

```bash
make install
cp .env.example .env
nano .env    # NVIDIA_API_KEY=nvapi-...

make start      # API http://127.0.0.1:8080 + Chainlit http://127.0.0.1:7860
make status
make demo
make health
make logs       # tail logs (Ctrl+C to exit)
make stop
make restart
```

Logs: `logs/api.log`, `logs/chainlit.log`

## Shell scripts (without Make)

```bash
chmod +x scripts/*.sh
./scripts/start.sh all
./scripts/status.sh
./scripts/stop.sh
```

## Environment (`.env`)

```env
LLM_PROFILE=multimodel
NIM_CLOUD_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_API_KEY=nvapi-...
CRISIS_USE_MOCK_LLM=false
API_BASE_URL=http://127.0.0.1:8080
SIMULATION_MODE=true
```

GPU instance runs the **app**; **LLM calls use NVIDIA cloud** unless agents are assigned `local_*` in `configs/llm/multimodel.yaml`.

## Manual run (foreground, two terminals)

```bash
source .venv/bin/activate
cp .env.example .env

# Terminal 1
set -a && source .env && set +a
.venv/bin/python -m uvicorn crisis.api.main:app --host 127.0.0.1 --port 8080

# Terminal 2
set -a && source .env && set +a
.venv/bin/chainlit run src/crisis/ui/chainlit_app.py --port 7860 --host 127.0.0.1
```

## Offline demo

```bash
export CRISIS_USE_MOCK_LLM=true
make demo
make test
```

## SSH access from your laptop

```bash
ssh -L 8080:127.0.0.1:8080 -L 7860:127.0.0.1:7860 ubuntu@<gpu-instance-ip>
```

Open `http://127.0.0.1:7860` locally.

## Optional: local NIM on Ubuntu

1. Run NIM on port `8000` (Docker or bare metal).
2. Set agent to `local_llama_8b` in `configs/llm/multimodel.yaml`.
3. Add `NIM_LOCAL_BASE_URL=http://127.0.0.1:8000/v1` to `.env`.
4. `make restart`

## Optional: Langfuse

Self-host Langfuse (Docker), set `LANGFUSE_*` in `.env`, then `make restart`.
