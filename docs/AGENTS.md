# Specialist agents

Each agent: `configs/agents/{agent_id}.yaml` — workflow selection + action pipeline.  
Router picks **who** runs; YAML defines **how**.

Diagram: [diagrams/orchestration.mmd](diagrams/orchestration.mmd) · [diagrams/agent-workflow.mmd](diagrams/agent-workflow.mmd)

## Catalog

| agent_id | Default workflow | LLM profile | Config |
|----------|----------------|-------------|--------|
| flood | flood_standard | cloud_nemotron_nano_8b | [flood.yaml](../configs/agents/flood.yaml) |
| utilities | utilities_standard | cloud_nemotron_nano_8b | [utilities.yaml](../configs/agents/utilities.yaml) |
| infrastructure | infra_standard | cloud_nemotron_nano_8b | [infrastructure.yaml](../configs/agents/infrastructure.yaml) |
| cyber | cyber_containment | cloud_nemotron_nano_8b | [cyber.yaml](../configs/agents/cyber.yaml) |
| comms | comms_standard | cloud_nemotron_nano_8b | [comms.yaml](../configs/agents/comms.yaml) |
| public_safety | public_safety_restricted | cloud_nemotron_nano_8b | [public_safety.yaml](../configs/agents/public_safety.yaml) |
| public_services | services_standard | cloud_phi_mini | [public_services.yaml](../configs/agents/public_services.yaml) |
| general | general_triage | cloud_nemotron_nano_8b | [general.yaml](../configs/agents/general.yaml) |

Assignments: [configs/llm/multimodel.yaml](../configs/llm/multimodel.yaml) · full table: [TECHNICAL_DESIGN §8.1](TECHNICAL_DESIGN.md).

## Action types

| type | Purpose |
|------|---------|
| tool | Skill from [registry.yaml](../configs/skills/registry.yaml) |
| llm | `draft_recommendation` |
| parallel | Concurrent `params.steps` |
| subagent | Child agent workflow (`CRISIS_MAX_SUBAGENT_DEPTH`, default 2) |
| critic / rule | Validation and deterministic branches |
| nat_workflow | Stub (future NAT integration) |

## Config reload

Change YAML → `make restart` (no hot-reload).

Optional override: `CRISIS_AGENT_WORKFLOWS=flood:flood_critical,utilities:utilities_hospital_priority`

## Code

`src/crisis/agents/specialist.py` · `workflow_engine.py` · `workflow_select.py` · `pipeline/runner.py`
