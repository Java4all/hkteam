from __future__ import annotations

from typing import Any

from crisis.models.enums import IncidentStatus
from crisis.models.schemas import HumanDecision, IncidentSummary, Recommendation


def _all_rec_ids(summary: IncidentSummary | None) -> set[str]:
    if not summary:
        return set()
    return {r.id for r in summary.ranked_recommendations}


def apply_human_decision(row: dict[str, Any], decision: HumanDecision) -> None:
    """Persist operator decision and apply per-recommendation edits to the summary."""
    summary: IncidentSummary | None = row.get("incident_summary")
    known = _all_rec_ids(summary)

    if known:
        approved = [rid for rid in decision.approved_recommendation_ids if rid in known]
    else:
        approved = list(decision.approved_recommendation_ids)
    rejected_raw = decision.rejected_recommendation_ids
    reject_all = "*" in rejected_raw
    rejected = [rid for rid in rejected_raw if rid != "*" and rid in known]

    if summary and decision.modified_recommendations:
        updated: list[Recommendation] = []
        for rec in summary.ranked_recommendations:
            if rec.id in decision.modified_recommendations:
                new_action = decision.modified_recommendations[rec.id].strip()
                if new_action:
                    updated.append(rec.model_copy(update={"action": new_action}))
                    continue
            updated.append(rec)
        summary = summary.model_copy(update={"ranked_recommendations": updated})
        row["incident_summary"] = summary

    if reject_all and not approved:
        rejected = list(known)

    row["human_decision"] = decision
    inc = row["incident"]
    if reject_all and not approved:
        inc.status = IncidentStatus.REJECTED
    elif approved:
        inc.status = IncidentStatus.APPROVED
    elif rejected and not approved:
        inc.status = IncidentStatus.REJECTED
    else:
        inc.status = IncidentStatus.AWAITING_HUMAN
