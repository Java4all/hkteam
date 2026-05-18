"""Parse specialist LLM markdown into SpecialistOutput."""

from __future__ import annotations

import re

from crisis.agents.recommendations import parse_recommendation_bullets
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import (
    CommunicationDraft,
    Evidence,
    Recommendation,
    SpecialistOutput,
)


def parse_llm_output(
    agent_id: str, workflow_id: str, text: str, evidence_raw: list[dict]
) -> SpecialistOutput:
    evidence = [
        Evidence(id=e["id"], source=e["source"], excerpt=e["excerpt"])
        for e in evidence_raw
    ]
    recs: list[Recommendation] = []
    for i, action in enumerate(parse_recommendation_bullets(text)):
        recs.append(
            Recommendation(
                id=f"rec-{agent_id}-{i+1}",
                priority=min(5, i + 1),
                action=action,
                rationale=f"From {agent_id} analysis ({workflow_id})",
                evidence_ids=[evidence[0].id] if evidence else [],
            )
        )
    if not recs:
        recs.append(
            Recommendation(
                id=f"rec-{agent_id}-1",
                priority=1,
                action=f"Review {agent_id} situation and confirm with field teams.",
                rationale="Default recommendation",
                evidence_ids=[evidence[0].id] if evidence else [],
            )
        )

    draft_body = ""
    if "## Communication" in text or "## communication" in text.lower():
        parts = re.split(r"##\s*Communication", text, flags=re.I)
        if len(parts) > 1:
            draft_body = parts[1].strip()[:800]

    drafts = []
    if draft_body:
        drafts.append(
            CommunicationDraft(
                id=f"com-{agent_id}-1",
                audience="city services",
                channel="internal_alert",
                body=draft_body,
                priority="HIGH",
            )
        )

    return SpecialistOutput(
        agent_id=agent_id,
        workflow_id=workflow_id,
        workflow_selection_rationale="",
        recommendations=recs,
        communication_drafts=drafts,
        evidence=evidence,
        checks_passed=True,
        confidence=0.8,
        status=SpecialistStatus.COMPLETE,
    )
