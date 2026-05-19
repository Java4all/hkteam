"""Chainlit operator console — run: chainlit run src/crisis/ui/chainlit_app.py"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Resolve project root (hkteam/) so public/favicon.* is found even when cwd differs.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("CHAINLIT_APP_ROOT", str(_PROJECT_ROOT))

import chainlit as cl
import httpx

from crisis.agents.display import agent_display_name, format_agent_list
from crisis.ui.pipeline_animator import PipelineProgressUI
from crisis.ui.welcome import format_welcome_message
from crisis.ui.pipeline_display import format_pipeline_stages
from crisis.ui.dispatch_animator import DispatchProgressUI, animate_dispatch_reveal
from crisis.ui.incident_history import format_incident_sidebar_html
from crisis.agents.recommendations import strip_recommendations_from_narrative
from crisis.ui.review_panel import (
    build_footer_actions,
    build_rec_card_actions,
    empty_review_state,
    format_rec_card,
    format_recommendations_header,
    review_cards_key,
    review_session_key,
    recommendations_for_review,
)

API = os.environ.get("API_BASE_URL", "http://127.0.0.1:8080")
_PIPELINE_TIMEOUT = float(os.environ.get("CRISIS_PIPELINE_TIMEOUT", "300"))
_SIDEBAR_KEY = "incident-history"


def _format_api_error(exc: httpx.HTTPError) -> str:
    parts = [f"**API error:** {exc}"]
    resp = getattr(exc, "response", None)
    if resp is not None:
        parts.append(f" HTTP {resp.status_code}")
        try:
            body = resp.json()
            if isinstance(body, dict):
                detail = body.get("detail", body)
                if isinstance(detail, dict):
                    if detail.get("message"):
                        parts.append(f"\n\n**Message:** {detail['message']}")
                    if detail.get("hint"):
                        parts.append(f"\n\n**Hint:** {detail['hint']}")
                else:
                    parts.append(f"\n\n```\n{detail}\n```")
        except Exception:
            text = resp.text[:800] if resp.text else ""
            if text:
                parts.append(f"\n\n```\n{text}\n```")
    parts.append(
        "\n\n_Check pipeline stages above, `docker compose logs api`, or `make diagnose-nvidia`._"
    )
    return "".join(parts)


async def _run_incident_stream(
    client: httpx.AsyncClient,
    description: str,
    location: str,
    ui: PipelineProgressUI,
) -> tuple[dict | None, list[dict], str | None]:
    stages: list[dict] = []
    result: dict | None = None
    error_msg: str | None = None

    async with client.stream(
        "POST",
        f"{API}/incidents/stream",
        json={"description": description, "location": location},
        timeout=_PIPELINE_TIMEOUT,
    ) as resp:
        if resp.status_code >= 400:
            body = (await resp.aread()).decode("utf-8", errors="replace")[:800]
            return None, stages, f"HTTP {resp.status_code}: {body}"

        async for line in resp.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "stages":
                stages = payload.get("stages") or stages
                await ui.set_stages(stages)
            elif payload.get("type") == "complete":
                result = payload
                stages = payload.get("pipeline_stages") or stages
                await ui.set_stages(stages)
            elif payload.get("type") == "error":
                error_msg = payload.get("message", "Pipeline failed")
                stages = payload.get("stages") or stages
                await ui.set_stages(stages)

    await ui.finish(stages, success=result is not None and not error_msg)
    return result, stages, error_msg


async def _run_incident_blocking(
    client: httpx.AsyncClient, description: str, location: str
) -> dict:
    r = await client.post(
        f"{API}/incidents",
        json={"description": description, "location": location},
        timeout=_PIPELINE_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


async def _fetch_incident_summaries() -> list[dict]:
    current_id = cl.user_session.get("incident_id")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{API}/incidents",
                params={"limit": 40, "current_id": current_id or ""},
            )
            r.raise_for_status()
            return list(r.json().get("incidents") or [])
    except Exception:
        return []


async def refresh_incident_sidebar() -> None:
    """Update element sidebar: Current incident + History tabs."""
    current_id = cl.user_session.get("incident_id")
    history = await _fetch_incident_summaries()
    current_summary = None
    if current_id:
        for row in history:
            if row.get("incident_id") == current_id:
                current_summary = row
                break
    html = format_incident_sidebar_html(
        current_id=current_id,
        current_summary=current_summary,
        history=history,
    )
    await cl.ElementSidebar.set_title("Incident console")
    await cl.ElementSidebar.set_elements(
        [
            cl.Text(
                name="incident_history_panel",
                content=html,
                display="side",
            )
        ],
        key=_SIDEBAR_KEY,
    )


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content=format_welcome_message()).send()
    await refresh_incident_sidebar()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if not text or len(text) < 12:
        await cl.Message(
            content=(
                "Incident report is incomplete. Provide a situation summary and "
                "affected location (location on the last line)."
            )
        ).send()
        return

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    location = lines[-1] if len(lines) > 1 else "city unknown"
    description = text if len(lines) == 1 else "\n".join(lines[:-1])

    data: dict | None = None
    stages: list[dict] = []
    ui = PipelineProgressUI()

    async with cl.Step(
        name="Multi-agent crisis analysis",
        type="run",
        show_input=False,
        default_open=True,
        auto_collapse=False,
    ) as pipeline_step:
        await ui.start(
            headline="_Orchestrating classify → route → specialists → briefing…_"
        )
        async with httpx.AsyncClient(timeout=_PIPELINE_TIMEOUT) as client:
            try:
                data, stages, stream_err = await _run_incident_stream(
                    client, description, location, ui
                )
                if stream_err and not data:
                    pipeline_step.output = format_pipeline_stages(stages)
                    await cl.Message(
                        content=(
                            f"### ❌ Pipeline failed\n\n**{stream_err}**\n\n"
                            + format_pipeline_stages(stages)
                        )
                    ).send()
                    return
                if not data:
                    data = await _run_incident_blocking(client, description, location)
                    stages = data.get("pipeline_stages", [])
                    await ui.finish(stages, success=True)
            except httpx.HTTPError as exc:
                await ui.finish(stages, success=False)
                pipeline_step.output = "Failed — see error message."
                await cl.Message(content=_format_api_error(exc)).send()
                return

        pipeline_step.output = (
            f"Completed {sum(1 for s in stages if s.get('status') == 'complete')}"
            f"/{len(stages)} stages"
        )

    iid = data["incident_id"]
    cl.user_session.set("incident_id", iid)

    routing = data.get("routing", {})
    summary = data.get("summary", {})
    agents = format_agent_list(routing.get("selected", []))
    narrative = strip_recommendations_from_narrative(summary.get("narrative", ""))
    selected = routing.get("selected") or []
    fallback_agent = selected[0] if selected else "eoc"
    pipeline_stages = stages or data.get("pipeline_stages", [])
    complete = sum(1 for s in pipeline_stages if s.get("status") == "complete")
    total = len(pipeline_stages)

    failed_agents = summary.get("agents_failed") or []
    failed_note = ""
    if failed_agents:
        failed_note = (
            "\n\n> ⚠️ **Specialists failed:** "
            + ", ".join(agent_display_name(a) for a in failed_agents)
        )

    await cl.Message(
        content=(
            f"## 🚨 Incident `{iid}`\n"
            f"**Severity:** {data.get('severity')} · "
            f"**Categories:** {', '.join(data.get('categories', []))}\n"
            f"**Specialists:** {agents}\n"
            f"**Routing:** {routing.get('rationale', '')}{failed_note}\n"
            f"**Pipeline:** {complete}/{total} stages complete "
            "(details in **Crisis Response Command Center** above).\n\n"
            f"### 📋 EOC Briefing\n{narrative}"
        ),
    ).send()

    review_recs = recommendations_for_review(
        summary, fallback_agent=fallback_agent
    )
    await _send_review_panel(iid, review_recs)
    await refresh_incident_sidebar()


async def _send_review_panel(iid: str, recs: list[dict]) -> None:
    if not recs:
        await cl.Message(content="## Recommendations\n\n_(none)_").send()
        return

    state = empty_review_state(recs)
    cl.user_session.set(review_session_key(iid), state)

    await cl.Message(
        content=format_recommendations_header(),
        tags=["crisis-rec-header"],
    ).send()

    card_msgs: dict[str, cl.Message] = {}
    for i, r in enumerate(recs):
        rid = r["id"]
        card = cl.Message(
            content=format_rec_card(i, r, state),
            actions=build_rec_card_actions(iid, rid, state),
            tags=["crisis-rec"],
        )
        await card.send()
        card_msgs[rid] = card
    cl.user_session.set(review_cards_key(iid), card_msgs)

    footer = cl.Message(
        content=(
            "### Finalize review\n\n"
            "Mark each recommendation, then **Submit** to record your decision "
            "and run the **dispatch simulation**."
        ),
        actions=build_footer_actions(iid),
        tags=["crisis-review-footer"],
    )
    await footer.send()
    cl.user_session.set(f"review_footer_{iid}", footer)


def _get_review_state(iid: str) -> dict | None:
    return cl.user_session.get(review_session_key(iid))


async def _refresh_rec_card(iid: str, rec_id: str) -> None:
    state = _get_review_state(iid)
    if not state:
        return
    cards: dict[str, cl.Message] = cl.user_session.get(review_cards_key(iid)) or {}
    msg = cards.get(rec_id)
    if not msg:
        return
    for i, r in enumerate(state["recommendations"]):
        if r["id"] == rec_id:
            old_actions = list(msg.actions)
            msg.actions = []
            for action in old_actions:
                await action.remove()
            msg.content = format_rec_card(i, r, state)
            msg.actions = build_rec_card_actions(iid, rec_id, state)
            await msg.update()
            break


@cl.action_callback("approve_rec")
async def approve_rec(action: cl.Action):
    iid = action.payload["id"]
    rec_id = action.payload["rec_id"]
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Session expired — run a new incident.").send()
        return
    if rec_id in state["approved"]:
        state["approved"].remove(rec_id)
    else:
        state["approved"].append(rec_id)
        if rec_id in state["rejected"]:
            state["rejected"].remove(rec_id)
    cl.user_session.set(review_session_key(iid), state)
    await _refresh_rec_card(iid, rec_id)


@cl.action_callback("reject_rec")
async def reject_rec(action: cl.Action):
    iid = action.payload["id"]
    rec_id = action.payload["rec_id"]
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Session expired — run a new incident.").send()
        return
    if rec_id in state["rejected"]:
        state["rejected"].remove(rec_id)
    else:
        state["rejected"].append(rec_id)
        if rec_id in state["approved"]:
            state["approved"].remove(rec_id)
    cl.user_session.set(review_session_key(iid), state)
    await _refresh_rec_card(iid, rec_id)


@cl.action_callback("submit_review")
async def submit_review(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    if not iid:
        await cl.Message(
            content="**No active incident.** Submit a new situation report to begin."
        ).send()
        return
    state = _get_review_state(iid)
    if not state:
        await cl.Message(
            content=(
                "**Review session expired** (page was refreshed or the tab was idle). "
                "Submit the incident again, or use **Approve all** then **Submit** "
                "before refreshing."
            )
        ).send()
        return
    recs = state["recommendations"]
    pending = [
        r["id"]
        for r in recs
        if r["id"] not in state["approved"] and r["id"] not in state["rejected"]
    ]
    if pending:
        await cl.Message(
            content=(
                f"**{len(pending)} recommendation(s) not decided.** "
                "Use Approve or Reject on each, or Approve all / Reject all."
            )
        ).send()
        return

    approved = list(state["approved"])
    dispatch_ui = DispatchProgressUI()

    async def _post() -> dict:
        return await _post_decision(
            iid,
            approved,
            list(state["rejected"]),
            None,
            dict(state["modified"]),
            recs,
        )

    try:
        resp = await animate_dispatch_reveal(
            dispatch_ui,
            approved_ids=approved,
            post_fn=_post,
        )
    except httpx.HTTPStatusError as exc:
        await cl.Message(content=_format_api_error(exc)).send()
        return
    except httpx.HTTPError as exc:
        await cl.Message(
            content=f"**Could not reach API** at `{API}` — {exc}"
        ).send()
        return
    except Exception as exc:
        await cl.Message(content=f"**Submit failed:** {exc}").send()
        return

    await cl.Message(content=_format_decision_result(resp)).send()
    await refresh_incident_sidebar()


@cl.action_callback("approve_all")
async def approve_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Session expired.").send()
        return
    state["approved"] = [r["id"] for r in state["recommendations"]]
    state["rejected"] = []
    cl.user_session.set(review_session_key(iid), state)
    for r in state["recommendations"]:
        await _refresh_rec_card(iid, r["id"])
    await cl.Message(
        content=(
            f"**All {len(state['approved'])} recommendations marked approved.** "
            "Select **Submit** when ready to finalize."
        )
    ).send()


@cl.action_callback("reject_all")
async def reject_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Session expired.").send()
        return
    state["rejected"] = [r["id"] for r in state["recommendations"]]
    state["approved"] = []
    cl.user_session.set(review_session_key(iid), state)
    for r in state["recommendations"]:
        await _refresh_rec_card(iid, r["id"])
    await cl.Message(
        content=(
            f"**All {len(state['rejected'])} recommendations marked rejected.** "
            "Select **Submit** when ready to finalize."
        )
    ).send()


def _format_decision_result(resp: dict) -> str:
    summary = resp.get("summary", {})
    return (
        f"**Decision recorded** — status `{resp.get('status', '?')}`\n\n"
        f"- Approved: {summary.get('approved_count', 0)}\n"
        f"- Rejected: {summary.get('rejected_count', 0)}\n"
        f"- Edited: {summary.get('modified_count', 0)}"
    )


async def _get_incident(iid: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(f"{API}/incidents/{iid}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


async def _post_decision(
    iid: str,
    approved: list[str],
    rejected: list[str],
    reason: str | None,
    modified: dict[str, str] | None = None,
    review_recommendations: list[dict] | None = None,
) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{API}/incidents/{iid}/decision",
            json={
                "operator_id": "chainlit-operator",
                "approved_recommendation_ids": approved,
                "rejected_recommendation_ids": rejected,
                "rejection_reason": reason,
                "modified_recommendations": modified or {},
                "review_recommendations": review_recommendations or [],
            },
        )
        r.raise_for_status()
        return r.json()
