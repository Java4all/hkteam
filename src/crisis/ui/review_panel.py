from __future__ import annotations

from typing import Any

import chainlit as cl

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import agent_id_from_recommendation_id

def review_session_key(incident_id: str) -> str:
    return f"review_{incident_id}"


def review_cards_key(incident_id: str) -> str:
    return f"review_cards_{incident_id}"


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


def build_rec_card_actions(
    incident_id: str, rec_id: str, state: dict[str, Any]
) -> list[cl.Action]:
    is_approved = rec_id in state["approved"]
    is_rejected = rec_id in state["rejected"]
    return [
        cl.Action(
            name="approve_rec",
            payload={"id": incident_id, "rec_id": rec_id},
            label="Undo Approve" if is_approved else "Approve",
        ),
        cl.Action(
            name="reject_rec",
            payload={"id": incident_id, "rec_id": rec_id},
            label="Undo Reject" if is_rejected else "Reject",
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
