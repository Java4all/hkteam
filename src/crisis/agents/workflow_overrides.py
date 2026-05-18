"""Per-agent workflow overrides from CRISIS_AGENT_WORKFLOWS env."""

from __future__ import annotations

from crisis.models.schemas import RouterHandoff
from crisis.settings import settings


def parse_agent_workflow_overrides(raw: str | None = None) -> dict[str, str]:
    text = (raw if raw is not None else settings.crisis_agent_workflows).strip()
    out: dict[str, str] = {}
    if not text:
        return out
    for part in text.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        agent, wf = part.split(":", 1)
        out[agent.strip()] = wf.strip()
    return out


def apply_workflow_override(handoff: RouterHandoff, agent_id: str) -> RouterHandoff:
    overrides = parse_agent_workflow_overrides()
    wf = overrides.get(agent_id)
    if wf:
        return handoff.model_copy(update={"workflow_override": wf})
    return handoff
