"""Build incident list summaries for API / operator sidebar."""

from __future__ import annotations

from typing import Any


def row_to_summary(row: dict[str, Any]) -> dict[str, Any]:
    inc = row["incident"]
    human = row.get("human_decision")
    summary = row.get("incident_summary")
    approved = len(human.approved_recommendation_ids) if human else 0
    rejected = (
        len([x for x in human.rejected_recommendation_ids if x != "*"])
        if human
        else 0
    )
    rec_total = len(summary.ranked_recommendations) if summary else 0
    return {
        "incident_id": inc.incident_id,
        "status": inc.status.value,
        "severity": inc.severity.value,
        "categories": [c.value for c in inc.categories],
        "location": inc.location,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "recommendation_count": rec_total,
        "approved_count": approved,
        "rejected_count": rejected,
        "has_decision": human is not None,
    }
