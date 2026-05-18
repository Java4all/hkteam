# Smart City Crisis Management AI

Multi-agent decision-support system for city emergency operations teams. The system ingests incident reports, classifies them, intelligently routes work to specialist AI agents, and presents actionable recommendations to a **human operator** for approval before any external action.

## Documentation

| Document | Description |
|----------|-------------|
| [**Technical Design**](docs/TECHNICAL_DESIGN.md) | **Primary build reference** — architecture, components, data models, LangGraph, NIM/NAT, phases |
| [Requirements](.kiro/specs/smart-city-crisis-management/requirements.md) | Product requirements (Kiro) |

## Stack

- **Orchestration:** LangGraph (incident graph + specialist subgraphs)
- **Inference:** NVIDIA NIM (`ChatNVIDIA`, local or cloud)
- **Tools / RAG (optional):** NeMo Agent Toolkit (NAT)
- **Observability:** LangSmith or Langfuse
- **API:** FastAPI + SSE streaming

## Configuration (samples)

- `configs/smart_routing/` — category map, Smart Router rules
- `configs/agents/` — per-specialist workflows and LLM config

## Status

Design phase — implementation follows [Technical Design §14](docs/TECHNICAL_DESIGN.md#14-implementation-phases).
