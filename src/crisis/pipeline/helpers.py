from __future__ import annotations

from crisis.llm.registry import resolve_profile
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import RouterHandoff, SpecialistOutput


def llm_stage_detail(agent_id: str) -> str:
    profile = resolve_profile(agent_id, "agent")
    model_short = profile.model.rsplit("/", 1)[-1]
    return f"{model_short} ({profile.llm_provider})"


def handoff_from_state(incident, routing) -> RouterHandoff:
    return RouterHandoff(
        incident_id=incident.incident_id,
        categories=[c.value for c in incident.categories],
        severity=incident.severity,
        location=incident.location,
        description=incident.description,
        confidence=incident.confidence,
        routing_hints=incident.routing_hints,
        activated_reason=routing.rationale,
    )


def failed_specialist_output(agent_id: str, workflow_id: str, error: str) -> SpecialistOutput:
    err_lower = error.lower()
    status = (
        SpecialistStatus.TIMEOUT
        if "timed out" in err_lower or "timeout" in err_lower
        else SpecialistStatus.FAILED
    )
    return SpecialistOutput(
        agent_id=agent_id,
        workflow_id=workflow_id or "unknown",
        workflow_selection_rationale="",
        recommendations=[],
        communication_drafts=[],
        evidence=[],
        checks_passed=False,
        check_notes=[error[:500]],
        confidence=0.0,
        status=status,
    )
