# Documentation index — Smart City Crisis Management v1.0

**Last reviewed:** 2026-05-18 (aligned with workflow-only agent orchestration)

## Start here

| Audience | Document |
|----------|----------|
| Deploy on NVIDIA GPU instance | [DOCKER.md](DOCKER.md) |
| Host prep (Ubuntu / Brev) | [UBUNTU.md](UBUNTU.md) |
| Day-2 operations | [RUNBOOK_v1.md](RUNBOOK_v1.md) |
| Architecture & models | [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) |
| **Agent workflows & orchestration** | [AGENTS.md](AGENTS.md) |
| Diagrams (Mermaid) | [diagrams/README.md](diagrams/README.md) |
| Demo incidents | [../data/examples/README.md](../data/examples/README.md) |
| Product requirements | [REQUIREMENTS.md](REQUIREMENTS.md) |

## v1.0 architecture (current)

```text
Docker Compose on NVIDIA GPU instance
  → Chainlit (operators) → API (LangGraph pipeline)
  → Smart Router: which specialists run (max 4 parallel)
  → Each specialist: configs/agents/{id}.yaml workflow
       (tool, llm, parallel, subagent, critic, rule, nat_workflow stub)
  → Aggregator → Human review → Dispatch simulation
  → LLM: NVIDIA cloud (multimodel.yaml) · Traces: Langfuse v3
```

## Key environment variables

| Variable | Purpose |
|----------|---------|
| `NVIDIA_API_KEY` | Cloud LLM on integrate.api.nvidia.com |
| `LLM_PROFILE=multimodel` | Per-role model assignments |
| `CRISIS_MAX_SUBAGENT_DEPTH` | Nested child-agent limit (default 2) |
| `CRISIS_AGENT_WORKFLOWS` | Optional force workflow per agent |
| `SIMULATION_MODE=true` | No real external dispatch |
| `LANGFUSE_*` | Self-hosted tracing (v3 stack in compose) |

## What is **not** in v1.0 docs as supported

- `CRISIS_WORKFLOW_MODE` legacy/hybrid (removed — YAML workflows only)
- Langfuse v2 single-container image
- Bare-metal production API/Chainlit (use Docker on GPU instance)
- Live NAT tool execution (`nat_workflow` action is a stub)

## Repository root

[../README.md](../README.md)
