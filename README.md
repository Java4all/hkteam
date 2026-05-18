# Smart City Crisis Management AI

**Version 1.0** — multi-agent decision-support for city emergency operations teams.

**Primary runtime:** Ubuntu (22.04+ recommended) on CPU/GPU cloud instances.

## Documentation

| Document | Description |
|----------|-------------|
| [**Ubuntu setup**](docs/UBUNTU.md) | **Start here on Ubuntu** |
| [**Runbook v1.0**](docs/RUNBOOK_v1.md) | Operations and LLM config |
| [**Technical Design v1.0**](docs/TECHNICAL_DESIGN.md) | Architecture |
| [Requirements](.kiro/specs/smart-city-crisis-management/requirements.md) | Product requirements |

## Stack

- **Orchestration:** LangGraph
- **Inference (default):** NVIDIA **cloud** — per-agent models (`LLM_PROFILE=multimodel`)
- **UI:** Chainlit · **API:** FastAPI · **Observability:** Langfuse (optional)

## Quick start (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv make curl

cd hkteam
make install
cp .env.example .env
nano .env                    # NVIDIA_API_KEY=nvapi-...

make demo                    # terminal demo
make start                   # API :8080 + Chainlit :7860
make status
# browser: http://127.0.0.1:7860

make stop
make restart
```

## Make commands

| Command | Description |
|---------|-------------|
| `make install` | Create `.venv`, install package |
| `make start` | Start API + Chainlit (background) |
| `make stop` | Stop services |
| `make restart` | Stop then start |
| `make status` | PIDs, ports, health |
| `make demo` | Run 3 demo scenarios |
| `make test` | `pytest` |
| `make health` | `curl /health` |
| `make logs` | Tail `logs/*.log` |

Shell scripts (without make): `./scripts/start.sh`, `./scripts/stop.sh`

## Offline demo (no API key)

```bash
export CRISIS_USE_MOCK_LLM=true
make demo
make test
```

## Configuration

| File | Purpose |
|------|---------|
| `configs/llm/multimodel.yaml` | **Default** — per-agent NVIDIA cloud models |
| `configs/llm/local.yaml` | Optional — all agents on local NIM |
| `configs/smart_routing/` | Smart Router rules |

## Project layout

```text
src/crisis/     Application code
scripts/        start.sh, stop.sh (Ubuntu)
tests/          pytest
configs/        LLM + routing YAML
data/           Synthetic knowledge base
```
