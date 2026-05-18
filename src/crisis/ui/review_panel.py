from __future__ import annotations

from typing import Any

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import agent_id_from_recommendation_id


def review_session_key(incident_id: str) -> str:
    return f"review_{incident_id}"


def empty_review_state(recommendations: list[dict]) -> dict[str, Any]:
    return {
        "recommendations": recommendations,
        "approved": [],
        "rejected": [],
        "modified": {},
    }


def _status_icon(rec_id: str, state: dict[str, Any]) -> str:
    if rec_id in state["approved"]:
        return "✅"
    if rec_id in state["rejected"]:
        return "❌"
    if rec_id in state["modified"]:
        return "✏️"
    return "⏳"


def format_review_panel(incident_id: str, state: dict[str, Any]) -> str:
    recs = state.get("recommendations") or []
    lines = [
        "## 👤 Operator review",
        "",
        "Review each recommendation **before dispatch** (simulation mode).",
        "",
        "| # | Status | Specialist | Action |",
        "| --- | --- | --- | --- |",
    ]
    for i, r in enumerate(recs):
        rid = r["id"]
        aid = agent_id_from_recommendation_id(rid)
        label = agent_display_name(aid) if aid else "Specialist"
        action = state.get("modified", {}).get(rid) or r.get("action", "")
        action = action.replace("|", "/")[:220]
        lines.append(
            f"| {i + 1} | {_status_icon(rid, state)} | {label} | {action} |"
        )

    pending = [
        r["id"]
        for r in recs
        if r["id"] not in state["approved"] and r["id"] not in state["rejected"]
    ]
    lines.extend(
        [
            "",
            f"**Summary:** {len(state['approved'])} approved · "
            f"{len(state['rejected'])} rejected · "
            f"{len(state['modified'])} edited · "
            f"{len(pending)} pending",
            "",
            "_Use the buttons on each row, then **Submit review**. "
            "Or use Approve all / Reject all._",
        ]
    )
    return "\n".join(lines)


def build_review_actions(incident_id: str, recommendations: list[dict]) -> list:
    import chainlit as cl

    actions: list[cl.Action] = []
    for i, r in enumerate(recommendations[:10]):
        rid = r["id"]
        n = i + 1
        actions.append(
            cl.Action(
                name="approve_rec",
                payload={"id": incident_id, "rec_id": rid, "idx": i},
                label=f"✅ #{n}",
            )
        )
        actions.append(
            cl.Action(
                name="reject_rec",
                payload={"id": incident_id, "rec_id": rid, "idx": i},
                label=f"❌ #{n}",
            )
        )
        actions.append(
            cl.Action(
                name="edit_rec",
                payload={"id": incident_id, "rec_id": rid, "idx": i},
                label=f"✏️ #{n}",
            )
        )
    actions.extend(
        [
            cl.Action(
                name="submit_review",
                payload={"id": incident_id},
                label="📤 Submit review",
            ),
            cl.Action(
                name="approve_all",
                payload={"id": incident_id},
                label="✅ Approve all",
            ),
            cl.Action(
                name="reject_all",
                payload={"id": incident_id},
                label="↩️ Reject all",
            ),
        ]
    )
    return actions
