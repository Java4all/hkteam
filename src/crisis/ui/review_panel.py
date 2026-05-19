from __future__ import annotations

from typing import Any

import chainlit as cl

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import (
    agent_id_from_recommendation_id,
    recommendations_from_narrative,
)

def review_session_key(incident_id: str) -> str:
    return f"review_{incident_id}"


def review_cards_key(incident_id: str) -> str:
    return f"review_cards_{incident_id}"


def _normalize_rec_dict(rec: dict) -> dict | None:
    action = (rec.get("action") or "").strip()
    if not action:
        return None
    rid = rec.get("id") or f"rec-unknown-{hash(action) % 100000}"
    return {
        "id": rid,
        "priority": rec.get("priority", 1),
        "action": action,
        "rationale": rec.get("rationale", ""),
        "evidence_ids": list(rec.get("evidence_ids") or []),
    }


def _merge_review_recs(primary: list[dict], extra: list[dict], *, max_items: int) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for r in primary + extra:
        key = (r.get("action") or "").lower().strip()[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(r)
        if len(merged) >= max_items:
            break
    return merged


def recommendations_for_review(
    summary: dict,
    *,
    fallback_agent: str | None = None,
    max_items: int = 12,
) -> list[dict]:
    """Ranked recommendations for the operator review panel, with narrative fallback."""
    raw = summary.get("ranked_recommendations") or []
    normalized = [n for r in raw if (n := _normalize_rec_dict(r))]
    ranked = unique_recommendations_for_review(normalized, max_items=max_items)

    narrative = summary.get("narrative") or ""
    agent = fallback_agent or "eoc"
    from_narrative = recommendations_from_narrative(
        narrative, agent_id=agent, max_items=max_items
    )

    if ranked and from_narrative:
        return _merge_review_recs(ranked, from_narrative, max_items=max_items)
    if ranked:
        return ranked
    return from_narrative


def unique_recommendations_for_review(recs: list[dict], *, max_items: int = 12) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for r in recs:
        key = (r.get("action") or "").lower().strip()[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)
        if len(unique) >= max_items:
            break
    return unique or list(recs[:max_items])


def empty_review_state(recommendations: list[dict]) -> dict[str, Any]:
    return {
        "recommendations": recommendations,
        "approved": [],
        "rejected": [],
        "modified": {},
    }


def format_recommendations_header() -> str:
    return (
        '<div class="crisis-rec-header">'
        "## Recommendations\n\n"
        "_Validate each item using the actions below, then Submit._"
        "</div>"
    )


def format_rec_card(index: int, rec: dict, state: dict[str, Any]) -> str:
    rid = rec["id"]
    aid = agent_id_from_recommendation_id(rid)
    specialist = agent_display_name(aid) if aid else "Specialist"
    action = state.get("modified", {}).get(rid) or rec.get("action", "")
    action = action.strip().replace("\n", " ")

    return (
        '<div class="crisis-rec-card">'
        f'<div class="crisis-rec-title">{index + 1}. {specialist}</div>'
        f'<p class="crisis-rec-body">{action}</p>'
        "</div>"
    )


def _action_id(incident_id: str, rec_id: str, kind: str) -> str:
    safe = rec_id.replace(":", "-")
    return f"crisis-{incident_id}-{safe}-{kind}"


def build_rec_card_actions(
    incident_id: str, rec_id: str, state: dict[str, Any]
) -> list[cl.Action]:
    is_approved = rec_id in state["approved"]
    is_rejected = rec_id in state["rejected"]
    if is_approved:
        return [
            cl.Action(
                name="approve_rec",
                id=_action_id(incident_id, rec_id, "approve"),
                payload={"id": incident_id, "rec_id": rec_id},
                label="Undo Approve",
            ),
        ]
    if is_rejected:
        return [
            cl.Action(
                name="reject_rec",
                id=_action_id(incident_id, rec_id, "reject"),
                payload={"id": incident_id, "rec_id": rec_id},
                label="Undo Reject",
            ),
        ]
    return [
        cl.Action(
            name="approve_rec",
            id=_action_id(incident_id, rec_id, "approve"),
            payload={"id": incident_id, "rec_id": rec_id},
            label="Approve",
        ),
        cl.Action(
            name="reject_rec",
            id=_action_id(incident_id, rec_id, "reject"),
            payload={"id": incident_id, "rec_id": rec_id},
            label="Reject",
        ),
    ]


def build_footer_actions(incident_id: str) -> list[cl.Action]:
    return [
        cl.Action(
            name="submit_review",
            payload={"id": incident_id},
            label="Submit",
        ),
        cl.Action(
            name="approve_all",
            payload={"id": incident_id},
            label="Approve all",
        ),
        cl.Action(
            name="reject_all",
            payload={"id": incident_id},
            label="Reject all",
        ),
    ]
