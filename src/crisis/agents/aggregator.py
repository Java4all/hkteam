from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

import re

from crisis.agents.display import format_agent_list
from crisis.llm.registry import get_llm, resolve_profile
from crisis.models.schemas import Incident, IncidentSummary, Recommendation, SpecialistOutput


def _dedupe_recommendations(recs: list[Recommendation]) -> list[Recommendation]:
    seen: set[str] = set()
    unique: list[Recommendation] = []
    for rec in recs:
        key = re.sub(r"\s+", " ", rec.action.lower().strip())[:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(rec)
    return unique


def aggregate_outputs(incident: Incident, outputs: dict[str, SpecialistOutput]) -> IncidentSummary:
    ranked: list[Recommendation] = []
    drafts = []
    failed: list[str] = []
    for agent_id, out in outputs.items():
        if out.status.value in ("failed", "timeout"):
            failed.append(agent_id)
        ranked.extend(out.recommendations)
        drafts.extend(out.communication_drafts)

    ranked.sort(key=lambda r: (r.priority, r.id))
    ranked = _dedupe_recommendations(ranked)
    for i, rec in enumerate(ranked):
        rec.priority = min(5, i + 1)

    conflicts: list[str] = []
    if "flood" in outputs and "utilities" in outputs:
        conflicts.append("Review flood vs utilities access routes for repair crews.")

    profile = resolve_profile(None, "aggregator")
    llm = get_llm(None, "aggregator")
    bullets = "\n".join(f"- {r.action}" for r in ranked[:12])
    summary_text = ""
    try:
        agent_names = format_agent_list(outputs)
        resp = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Write a concise EOC briefing in Markdown for the human operator. "
                        "If you list involved specialists, use only their role names "
                        "(e.g. Flood, Utilities) — do not mention workflow IDs, model names, "
                        "or cloud/local provider."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Incident: {incident.description}\nLocation: {incident.location}\n"
                        f"Severity: {incident.severity.value}\n\n"
                        f"Involved specialists: {agent_names}\n\n"
                        f"Recommendations:\n{bullets}"
                    )
                ),
            ]
        )
        summary_text = getattr(resp, "content", str(resp))
    except Exception as exc:
        summary_text = f"Aggregator LLM unavailable: {exc}\n\n" + bullets if bullets else ""

    return IncidentSummary(
        incident_id=incident.incident_id,
        categories=incident.categories,
        severity=incident.severity,
        agent_outputs=outputs,
        ranked_recommendations=ranked,
        communication_drafts=drafts,
        conflicts=conflicts,
        agents_failed=failed,
        narrative=summary_text,
        ready_for_human_review=True,
    )
