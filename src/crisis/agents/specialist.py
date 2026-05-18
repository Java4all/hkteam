from __future__ import annotations

import re
import time
import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from crisis.agents.workflow_select import select_workflow
from crisis.llm.registry import get_llm, resolve_profile
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import (
    CommunicationDraft,
    Evidence,
    Recommendation,
    RouterHandoff,
    SpecialistOutput,
)
from crisis.skills.knowledge import enrich_agent_context


def _parse_llm_output(agent_id: str, workflow_id: str, text: str, evidence_raw: list[dict]) -> SpecialistOutput:
    evidence = [
        Evidence(id=e["id"], source=e["source"], excerpt=e["excerpt"])
        for e in evidence_raw
    ]
    recs: list[Recommendation] = []
    for i, line in enumerate(re.findall(r"^[-*]\s+(.+)$", text, re.M)):
        recs.append(
            Recommendation(
                id=f"rec-{agent_id}-{i+1}",
                priority=min(5, i + 1),
                action=line.strip(),
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


def run_specialist(agent_id: str, handoff: RouterHandoff) -> SpecialistOutput:
    t0 = time.perf_counter()
    workflow_id, rationale = select_workflow(agent_id, handoff)
    blob, evidence_raw = enrich_agent_context(
        agent_id, handoff.description, handoff.location, handoff.routing_hints
    )

    profile = resolve_profile(agent_id, "agent")
    llm = get_llm(agent_id, "agent")
    sys = SystemMessage(
        content=(
            f"You are the {agent_id} specialist for a city crisis EOC. "
            "Use ONLY the context provided. Output Markdown with:\n"
            "## Summary\n## Recommendations (bullet list)\n## Communication\n"
        )
    )
    human = HumanMessage(
        content=(
            f"Workflow: {workflow_id}\n"
            f"Severity: {handoff.severity.value}\n"
            f"Categories: {', '.join(handoff.categories)}\n\n"
            f"Context:\n{blob}"
        )
    )
    resp = llm.invoke([sys, human])
    text = getattr(resp, "content", str(resp))

    out = _parse_llm_output(agent_id, workflow_id, text, evidence_raw)
    out.workflow_selection_rationale = rationale
    out.duration_ms = int((time.perf_counter() - t0) * 1000)
    out.llm_profile = profile.profile_id
    out.llm_model = profile.model
    out.llm_provider = profile.llm_provider
    return out
