"""Chainlit operator console — run: chainlit run src/crisis/ui/chainlit_app.py"""

from __future__ import annotations

import os

import chainlit as cl
import httpx

API = os.environ.get("API_BASE_URL", "http://127.0.0.1:8080")


@cl.on_chat_start
async def start():
    await cl.Message(
        content=(
            "**Smart City Crisis Management** (v1.0)\n\n"
            "Describe an incident (what happened + location). Example:\n"
            "> Water main burst on Oak Street near City General Hospital. Flooding in road."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if not text or len(text) < 12:
        await cl.Message(content="Please provide at least 12 characters (description + location).").send()
        return

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    location = lines[-1] if len(lines) > 1 else "city unknown"
    description = text if len(lines) == 1 else "\n".join(lines[:-1])

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            r = await client.post(
                f"{API}/incidents",
                json={"description": description, "location": location},
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            await cl.Message(content=f"API error: {exc}").send()
            return

    iid = data["incident_id"]
    cl.user_session.set("incident_id", iid)

    routing = data.get("routing", {})
    summary = data.get("summary", {})
    agents = ", ".join(routing.get("selected", []))
    narrative = summary.get("narrative", "")
    recs = summary.get("ranked_recommendations", [])

    rec_lines = "\n".join(f"{i+1}. [{r['priority']}] {r['action']}" for i, r in enumerate(recs[:8]))
    trace = "\n".join(f"- {t}" for t in data.get("trace", [])[-8:])

    actions = [
        cl.Action(name="approve_all", payload={"id": iid}, label="Approve all recommendations"),
        cl.Action(name="reject_all", payload={"id": iid}, label="Reject (request revision)"),
    ]

    await cl.Message(
        content=(
            f"### Incident `{iid}`\n"
            f"**Severity:** {data.get('severity')} | **Categories:** {', '.join(data.get('categories', []))}\n"
            f"**Specialists activated:** {agents}\n"
            f"**Routing:** {routing.get('rationale', '')}\n\n"
            f"### Briefing\n{narrative}\n\n"
            f"### Recommendations\n{rec_lines or '(none)'}\n\n"
            f"### Trace\n{trace}"
        ),
        actions=actions,
    ).send()


@cl.action_callback("approve_all")
async def approve_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    row = await _get_incident(iid)
    if not row:
        await cl.Message(content="Incident not found.").send()
        return
    rec_ids = [r["id"] for r in (row.get("incident_summary") or {}).get("ranked_recommendations", [])]
    await _post_decision(iid, rec_ids, [], None)
    await cl.Message(content=f"Approved {len(rec_ids)} recommendation(s). SIMULATION: no external dispatch.").send()


@cl.action_callback("reject_all")
async def reject_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    await _post_decision(iid, [], ["*"], "Operator requested revision")
    await cl.Message(content="Incident marked rejected — revise and resubmit.").send()


async def _get_incident(iid: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(f"{API}/incidents/{iid}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def _post_decision(iid: str, approved: list[str], rejected: list[str], reason: str | None):
    async with httpx.AsyncClient(timeout=60.0) as client:
        await client.post(
            f"{API}/incidents/{iid}/decision",
            json={
                "operator_id": "chainlit-operator",
                "approved_recommendation_ids": approved,
                "rejected_recommendation_ids": rejected,
                "rejection_reason": reason,
            },
        )
