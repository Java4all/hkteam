# Specialist agents — orchestration and workflows

Every specialist runs a **declarative workflow** in `configs/agents/{agent_id}.yaml`. The incident orchestrator (LangGraph + pipeline) selects **which agents** run; each agent’s YAML defines **how** it runs (tools, LLM, child agents).

## Orchestration layers

```text
Smart Router          →  which agents (flood, utilities, cyber, …)
Per-agent workflow    →  how each agent runs (actions pipeline)
Aggregator            →  merge specialist outputs
Human review          →  approve / reject / submit
```

Diagram: [diagrams/agent-workflow.mmd](diagrams/agent-workflow.mmd)

## Agent catalog

| agent_id | Role | Config | Default workflow | LLM profile |
|----------|------|--------|------------------|-------------|
| `flood` | flood_coordinator | [flood.yaml](../configs/agents/flood.yaml) | `flood_standard` | `cloud_nemotron_nano_8b` |
| `utilities` | utilities_coordinator | [utilities.yaml](../configs/agents/utilities.yaml) | `utilities_standard` | `cloud_nemotron_nano_8b` |
| `infrastructure` | infrastructure_coordinator | [infrastructure.yaml](../configs/agents/infrastructure.yaml) | `infra_standard` | `cloud_nemotron_nano_8b` |
| `cyber` | cyber_coordinator | [cyber.yaml](../configs/agents/cyber.yaml) | `cyber_containment` | `cloud_mistral_7b` |
| `comms` | comms_coordinator | [comms.yaml](../configs/agents/comms.yaml) | `comms_standard` | `cloud_nemotron_nano_8b` |
| `public_safety` | eoc_safety_liaison | [public_safety.yaml](../configs/agents/public_safety.yaml) | `public_safety_restricted` | `cloud_nemotron_nano_8b` |
| `public_services` | service_continuity_lead | [public_services.yaml](../configs/agents/public_services.yaml) | `services_standard` | `cloud_phi_mini` |
| `general` | fallback_analyst | [general.yaml](../configs/agents/general.yaml) | `general_triage` | `cloud_nemotron_nano_8b` |

Models: `configs/llm/multimodel.yaml` · details in [TECHNICAL_DESIGN §8.1.3](TECHNICAL_DESIGN.md).

## Workflow action types

| type | Purpose | Example |
|------|---------|---------|
| `tool` | Registered skill (RAG, weather stub, GIS stub) | `playbook_rag` |
| `llm` | Schema-bound draft via `draft_recommendation` skill | `analyze` step |
| `parallel` | Run multiple tool/llm steps concurrently | flood `context` (weather + GIS) |
| `subagent` | Invoke **another agent’s** workflow as a child step | flood `flood_dam_breach` → `comms` |
| `critic` | Validate prior LLM output | `require_citations` |
| `rule` | Deterministic branch / escalation hint | CRITICAL escalation emit |
| `nat_workflow` | NeMo Agent Toolkit delegate (stub in v1.0) | future `configs/nat/` |

Skills registry: [configs/skills/registry.yaml](../configs/skills/registry.yaml).

### Subagent (child agent)

Runs a full workflow for another `agent_id` inside the parent workflow (depth capped):

```yaml
- id: comms
  type: subagent
  params:
    agent_id: comms
    workflow: comms_standard
  depends_on: [analyze]
```

```env
CRISIS_MAX_SUBAGENT_DEPTH=2
```

### Parallel tools

```yaml
- id: context
  type: parallel
  params:
    steps:
      - { id: weather, type: tool, skill: weather_api }
      - { id: zone, type: tool, skill: flood_zone_gis }
  depends_on: [kb]
```

## Workflow selection

1. `workflow_override` on handoff (human / `CRISIS_AGENT_WORKFLOWS`)
2. `configs/agents/*_selector_rules.yaml` when `rules_file` is set
3. `workflow_selection.default` in agent YAML

## Environment

```env
CRISIS_MAX_SUBAGENT_DEPTH=2
# CRISIS_AGENT_WORKFLOWS=flood:flood_critical,utilities:utilities_hospital_priority
```

Missing `configs/agents/{id}.yaml` for a routed agent → `AgentConfigError` (pipeline records specialist failure).

## Code map

| Concern | Location |
|---------|----------|
| Entry | `src/crisis/agents/specialist.py` → `run_specialist()` |
| Action runner | `src/crisis/agents/workflow_engine.py` |
| YAML load | `src/crisis/agents/config_loader.py` |
| Workflow pick | `src/crisis/agents/workflow_select.py` |
| Parallel fan-out (incident) | `src/crisis/pipeline/runner.py` |
| Smart Router | `src/crisis/routing/smart_router.py` |
