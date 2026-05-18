from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from crisis.models.enums import Category, IncidentStatus, SeverityLevel, SpecialistStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentReport(BaseModel):
    description: str
    location: str
    reporter: str | None = None
    channel: str | None = None


class Evidence(BaseModel):
    id: str
    source: str
    excerpt: str


class Recommendation(BaseModel):
    id: str
    priority: int = Field(ge=1, le=5)
    action: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class CommunicationDraft(BaseModel):
    id: str
    audience: str
    channel: str
    body: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"


class Incident(BaseModel):
    incident_id: str
    description: str
    location: str
    categories: list[Category]
    severity: SeverityLevel
    confidence: float
    routing_hints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    original_report: IncidentReport
    status: IncidentStatus = IncidentStatus.PENDING
    category_confidence: dict[str, float] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    incident_id: str
    candidates: list[str]
    selected: list[str]
    deferred: list[str]
    selection_mode: Literal["minimal", "targeted", "full", "override"]
    execution_mode: Literal["parallel", "sequential"]
    rationale: str
    confidence: float


class SpecialistOutput(BaseModel):
    agent_id: str
    workflow_id: str
    workflow_selection_rationale: str
    recommendations: list[Recommendation]
    communication_drafts: list[CommunicationDraft]
    evidence: list[Evidence]
    checks_passed: bool = True
    check_notes: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    duration_ms: int = 0
    status: SpecialistStatus = SpecialistStatus.COMPLETE
    llm_profile: str = ""
    llm_model: str = ""
    llm_provider: str = ""


class RouterHandoff(BaseModel):
    incident_id: str
    categories: list[str]
    severity: SeverityLevel
    location: str
    description: str
    confidence: float
    routing_hints: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    activated_reason: str = ""
    prior_outputs: dict[str, SpecialistOutput] = Field(default_factory=dict)
    workflow_override: str | None = None


class IncidentSummary(BaseModel):
    incident_id: str
    categories: list[Category]
    severity: SeverityLevel
    agent_outputs: dict[str, SpecialistOutput]
    ranked_recommendations: list[Recommendation]
    communication_drafts: list[CommunicationDraft]
    conflicts: list[str] = Field(default_factory=list)
    agents_failed: list[str] = Field(default_factory=list)
    narrative: str = ""
    ready_for_human_review: bool = True


class HumanDecision(BaseModel):
    operator_id: str
    approved_recommendation_ids: list[str] = Field(default_factory=list)
    rejected_recommendation_ids: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None
    modified_drafts: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


def new_incident_id() -> str:
    return f"INC-{uuid4().hex[:12].upper()}"
