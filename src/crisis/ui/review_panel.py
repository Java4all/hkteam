from __future__ import annotations

from typing import Any

import chainlit as cl

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import (
    agent_id_from_recommendation_id,
    is_status_observation_line,
    is_valid_recommendation_line,
    normalize_recommendation_key,
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
    if not is_valid_recommendation_line(action):
        return None
    rid = rec.get("id") or f"rec-unknown-{hash(action) % 100000}"
    return {
        "id": rid,
        "priority": rec.get("priority", 1),
        "action": action,
        "rationale": rec.get("rationale", ""),
        "evidence_ids": list(rec.get("evidence_ids") or []),
    }


def _is_duplicate_key(key: str, seen: set[str]) -> bool:
    if key in seen:
        return True
    for existing in seen:
        if len(key) < 18 or len(existing) < 18:
            continue
        if key in existing or existing in key:
            return True
    return False


def unique_recommendations_for_review(recs: list[dict], *, max_items: int = 12) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for r in recs:
        action = (r.get("action") or "").strip()
        if not action or is_status_observation_line(action):
            continue
        key = normalize_recommendation_key(action)
        if not key or _is_duplicate_key(key, seen):
            continue
        seen.add(key)
        unique.append(r)
        if len(unique) >= max_items:
            break
    return unique


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

    if ranked:
        for i, rec in enumerate(ranked):
            rec["priority"] = min(5, i + 1)
            rec["id"] = f"rec-{fallback_agent or 'eoc'}-{i + 1}"
        return ranked

    narrative = summary.get("narrative") or ""
    agent = fallback_agent or "eoc"
    return recommendations_from_narrative(narrative, agent_id=agent, max_items=max_items)


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
        '<div class="crisis-rec-card" style="margin:0.35rem 0;padding:0.5rem 0;">'
        f'<div class="crisis-rec-title" style="font-weight:600;margin-bottom:0.35rem;">{index + 1}. {specialist}</div>'
        f'<p class="crisis-rec-body" style="margin:0;line-height:1.45;">{action}</p>'
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
