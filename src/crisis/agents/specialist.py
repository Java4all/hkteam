"""Specialist agents — each agent runs a YAML-defined workflow (tools, LLM, subagents)."""

from __future__ import annotations

from crisis.agents.config_loader import load_agent_config
from crisis.agents.workflow_engine import run_agent_workflow
from crisis.agents.workflow_progress import SpecialistStepCallback
from crisis.agents.workflow_select import select_workflow
from crisis.models.schemas import RouterHandoff, SpecialistOutput
from crisis.agents.errors import AgentConfigError
from crisis.settings import settings


def run_specialist(
    agent_id: str,
    handoff: RouterHandoff,
    *,
    depth: int = 0,
    on_step: SpecialistStepCallback | None = None,
) -> SpecialistOutput:
    """
    Run the specialist's configured workflow (configs/agents/{agent_id}.yaml).

    Workflows may invoke tools, LLM skills, parallel branches, child agents (subagent),
    or NAT workflow stubs. Child depth is capped by CRISIS_MAX_SUBAGENT_DEPTH.
    """
    if depth > settings.crisis_max_subagent_depth:
        raise AgentConfigError(
            f"Subagent depth {depth} exceeds limit {settings.crisis_max_subagent_depth}"
        )

    config = load_agent_config(agent_id)
    if not config or not config.workflows:
        raise AgentConfigError(
            f"No workflow for agent {agent_id!r}. "
            f"Add configs/agents/{agent_id}.yaml with at least one workflow."
        )

    workflow_id, rationale = select_workflow(agent_id, handoff, config=config)
    return run_agent_workflow(
        agent_id,
        workflow_id,
        handoff,
        config,
        selection_rationale=rationale,
        depth=depth,
        child_runner=_run_child_agent,
        on_step=on_step,
    )


def _run_child_agent(
    child_id: str,
    handoff: RouterHandoff,
    workflow_id: str | None,
    depth: int,
) -> SpecialistOutput:
    """Invoke another specialist workflow from a parent workflow (subagent action)."""
    config = load_agent_config(child_id)
    if not config or not config.workflows:
        raise AgentConfigError(f"No workflow for subagent {child_id!r}")

    if workflow_id and workflow_id in config.workflows:
        wf_id, rationale = workflow_id, f"subagent:fixed:{workflow_id}"
    elif handoff.workflow_override and handoff.workflow_override in config.workflows:
        wf_id, rationale = handoff.workflow_override, "subagent:override"
    else:
        wf_id, rationale = select_workflow(child_id, handoff, config=config)

    child_handoff = handoff.model_copy(
        update={
            "activated_reason": f"subagent:{child_id}",
            "workflow_override": wf_id if workflow_id else handoff.workflow_override,
        }
    )
    return run_agent_workflow(
        child_id,
        wf_id,
        child_handoff,
        config,
        selection_rationale=rationale,
        depth=depth,
        child_runner=_run_child_agent,
    )
