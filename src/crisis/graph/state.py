from __future__ import annotations

from typing import Any, TypedDict

from crisis.models.schemas import (
    HumanDecision,
    Incident,
    IncidentReport,
    IncidentSummary,
    RoutingDecision,
    SpecialistOutput,
)


class IncidentState(TypedDict, total=False):
    report: IncidentReport
    incident: Incident
    routing_decision: RoutingDecision
    specialist_outputs: dict[str, SpecialistOutput]
    incident_summary: IncidentSummary
    human_decision: HumanDecision
    trace: list[str]
    error: str
