from __future__ import annotations

from crisis.models.enums import SeverityLevel
from crisis.models.schemas import RouterHandoff

_DEFAULT = {
    "flood": "flood_standard",
    "cyber": "cyber_containment",
    "utilities": "utilities_standard",
    "infrastructure": "infra_standard",
    "public_safety": "public_safety_restricted",
    "public_services": "services_standard",
    "comms": "comms_standard",
    "general": "general_triage",
}


def select_workflow(agent_id: str, handoff: RouterHandoff) -> tuple[str, str]:
    if handoff.workflow_override:
        return handoff.workflow_override, "workflow_override"

    hints = set(handoff.routing_hints)
    if agent_id == "flood" and "dam" in hints:
        return "flood_dam_breach", "hint:dam"
    if agent_id == "flood" and handoff.severity == SeverityLevel.CRITICAL:
        return "flood_critical", "severity:CRITICAL"
    if agent_id == "utilities" and "hospital" in hints:
        return "utilities_hospital_priority", "hint:hospital"
    if agent_id == "cyber" and "ransomware" in hints:
        return "cyber_containment", "hint:ransomware"

    wf = _DEFAULT.get(agent_id, "general_triage")
    return wf, "default"
