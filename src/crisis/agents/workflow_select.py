"""Select workflow_id for a specialist from YAML rules and defaults."""

from __future__ import annotations

from crisis.agents.config_loader import AgentConfig, load_agent_config
from crisis.agents.errors import AgentConfigError
from crisis.agents.workflow_rules import evaluate_workflow_rules
from crisis.models.schemas import RouterHandoff


def select_workflow(
    agent_id: str,
    handoff: RouterHandoff,
    config: AgentConfig | None = None,
) -> tuple[str, str]:
    if config is None:
        config = load_agent_config(agent_id)

    if not config or not config.workflows:
        raise AgentConfigError(
            f"Cannot select workflow: missing configs/agents/{agent_id}.yaml"
        )

    if handoff.workflow_override and handoff.workflow_override in config.workflows:
        return handoff.workflow_override, "workflow_override"

    default = config.workflow_selection.default or next(iter(config.workflows))
    allowed = list(config.workflows.keys())
    return evaluate_workflow_rules(
        handoff,
        config.rules_path,
        default_workflow=default,
        allowed=allowed,
    )
