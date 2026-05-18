from __future__ import annotations

from typing import Any

import chainlit as cl

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import agent_id_from_recommendation_id


def review_session_key(incident_id: str) -> str:
    return f"review_{incident_id}"


def review_cards_key(incident_id: str) -> str:
    return f"review_cards_{incident_id}"


def review_summary_key(incident_id: str) -> str:
    return f"review_summary_{incident_id}"


def unique_recommendations_for_review(recs: list[dict], *, max_items: int = 12) -> list[dict]:
    """Collapse duplicate action text so the review UI is not repetitive."""
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


def _counts(state: dict[str, Any]) -> tuple[int, int, int, int]:
    recs = state.get("recommendations") or []
    approved = len(state["approved"])
    rejected = len(state["rejected"])
    edited = len(state["modified"])
    pending = sum(
        1
        for r in recs
        if r["id"] not in state["approved"] and r["id"] not in state["rejected"]
    )
    return approved, rejected, edited, pending


def format_review_summary(incident_id: str, state: dict[str, Any]) -> str:
    recs = state.get("recommendations") or []
    approved, rejected, edited, pending = _counts(state)
    total = len(recs)
    done = approved + rejected
    width = 16
    filled = int(width * done / max(total, 1))
    bar = f"`{'█' * filled}{'░' * (width - filled)}`"

    return (
        "## 👤 Operator review\n\n"
        "Review each recommendation card below, then **Submit review** at the bottom.\n\n"
        f"**Progress** {bar} {done}/{total}\n\n"
        f"| ✅ Approved | ❌ Rejected | ✏️ Edited | ⏳ Pending |\n"
        f"| ---: | ---: | ---: | ---: |\n"
        f"| {approved} | {rejected} | {edited} | {pending} |"
    )


def _status_label(rec_id: str, state: dict[str, Any]) -> tuple[str, str]:
    if rec_id in state["approved"]:
        return "✅ Approved", "approved"
    if rec_id in state["rejected"]:
        return "❌ Rejected", "rejected"
    if rec_id in state["modified"]:
        return "✏️ Edited (pending)", "edited"
    return "⏳ Pending", "pending"


def format_rec_card(index: int, rec: dict, state: dict[str, Any]) -> str:
    rid = rec["id"]
    aid = agent_id_from_recommendation_id(rid)
    specialist = agent_display_name(aid) if aid else "Specialist"
    status, _ = _status_label(rid, state)
    action = state.get("modified", {}).get(rid) or rec.get("action", "")
    action = action.strip()

    return (
        f"### Recommendation {index + 1} — {specialist}\n"
        f"**Status:** {status}\n\n"
        f"> {action}\n"
    )


def build_rec_card_actions(
    incident_id: str, rec_id: str, index: int, state: dict[str, Any]
) -> list[cl.Action]:
    is_approved = rec_id in state["approved"]
    is_rejected = rec_id in state["rejected"]
    return [
        cl.Action(
            name="approve_rec",
            payload={"id": incident_id, "rec_id": rec_id, "idx": index},
            label="Undo approve" if is_approved else "Approve",
        ),
        cl.Action(
            name="reject_rec",
            payload={"id": incident_id, "rec_id": rec_id, "idx": index},
            label="Undo reject" if is_rejected else "Reject",
        ),
        cl.Action(
            name="edit_rec",
            payload={"id": incident_id, "rec_id": rec_id, "idx": index},
            label="Edit text",
        ),
    ]


def build_footer_actions(incident_id: str) -> list[cl.Action]:
    return [
        cl.Action(
            name="submit_review",
            payload={"id": incident_id},
            label="Submit review",
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
