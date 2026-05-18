"""Chainlit operator console — run: chainlit run src/crisis/ui/chainlit_app.py"""

from __future__ import annotations

import json
import os
from pathlib import Path

import chainlit as cl
import httpx
import yaml

from crisis.agents.display import agent_display_name, format_agent_list
from crisis.agents.recommendations import agent_id_from_recommendation_id
from crisis.ui.pipeline_animator import PipelineProgressUI
from crisis.ui.pipeline_display import format_pipeline_stages, format_trace
from crisis.ui.review_panel import (
    build_footer_actions,
    build_rec_card_actions,
    empty_review_state,
    format_rec_card,
    format_review_summary,
    review_cards_key,
    review_session_key,
    review_summary_key,
    unique_recommendations_for_review,
)

API = os.environ.get("API_BASE_URL", "http://127.0.0.1:8080")
_PIPELINE_TIMEOUT = float(os.environ.get("CRISIS_PIPELINE_TIMEOUT", "300"))
_EXAMPLES_YAML = Path(__file__).resolve().parents[3] / "data" / "examples" / "incidents.yaml"


def _format_incident_message(description: str, location: str) -> str:
    desc = description.strip()
    loc = location.strip()
    return f"{desc}\n{loc}" if loc else desc


def _load_example_incidents() -> list[dict]:
    if not _EXAMPLES_YAML.is_file():
        return []
    data = yaml.safe_load(_EXAMPLES_YAML.read_text(encoding="utf-8")) or {}
    return list(data.get("examples") or [])


def _format_rec(i: int, r: dict) -> str:
    aid = agent_id_from_recommendation_id(r.get("id", ""))
    label = agent_display_name(aid) if aid else "Specialist"
    return f"{i + 1}. **{label}** — {r['action']}"


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
            elif payload.get("type") == "error":
                error_msg = payload.get("message", "Pipeline failed")
                stages = payload.get("stages") or stages

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


@cl.set_starters
async def set_starters():
    starters = []
    for ex in _load_example_incidents():
        desc = (ex.get("description") or "").strip()
        loc = (ex.get("location") or "").strip()
        if not desc:
            continue
        starters.append(
            cl.Starter(
                label=ex.get("label") or ex.get("id", "Incident"),
                message=_format_incident_message(desc, loc),
            )
        )
    if starters:
        return starters
    return [
        cl.Starter(
            label="Water main burst",
            message=_format_incident_message(
                "Major water main rupture. Water flooding Oak Street, low pressure in sectors 6–8.",
                "Oak Street, Sector 7",
            ),
        ),
    ]


@cl.on_chat_start
async def start():
    await cl.Message(
        content=(
            "## 🏙️ Smart City Crisis Management\n"
            "**Multi-agent AI command center** for emergency operations (v1.0)\n\n"
            "Click a **starter** scenario or paste an incident (`data/examples/*.txt` — "
            "last line = location).\n\n"
            "You will see a **live animated pipeline**: classify → route → parallel "
            "specialists (NVIDIA NeMo) → EOC briefing.\n\n"
            "Then use **Operator review** to approve, reject, or edit **each** "
            "recommendation before submit.\n\n"
            "**Example**\n"
            "> Heavy rainfall and water main break near City General Hospital…\n"
            "> Sector 7 riverside, Memorial Bridge approach"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    text = message.content.strip()
    if not text or len(text) < 12:
        await cl.Message(
            content="Please provide at least 12 characters (description + location)."
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
    narrative = summary.get("narrative", "")
    recs = summary.get("ranked_recommendations", [])
    rec_lines = "\n".join(_format_rec(i, r) for i, r in enumerate(recs[:12]))
    trace = format_trace(data.get("trace", []))
    stage_table = format_pipeline_stages(stages or data.get("pipeline_stages", []))

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
            f"**Routing:** {routing.get('rationale', '')}{failed_note}\n\n"
            f"### Pipeline summary\n{stage_table}\n\n"
            f"### 📋 EOC Briefing\n{narrative}\n\n"
            f"### Recommendations (preview)\n{rec_lines or '_(none)_'}\n\n"
            f"### Trace\n{trace}"
        ),
    ).send()

    review_recs = unique_recommendations_for_review(recs)
    await _send_review_panel(iid, review_recs)


async def _send_review_panel(iid: str, recs: list[dict]) -> None:
    state = empty_review_state(recs)
    cl.user_session.set(review_session_key(iid), state)

    summary = cl.Message(content=format_review_summary(iid, state))
    await summary.send()
    cl.user_session.set(review_summary_key(iid), summary)

    card_msgs: dict[str, cl.Message] = {}
    for i, r in enumerate(recs):
        rid = r["id"]
        card = cl.Message(
            content=format_rec_card(i, r, state),
            actions=build_rec_card_actions(iid, rid, i, state),
        )
        await card.send()
        card_msgs[rid] = card
    cl.user_session.set(review_cards_key(iid), card_msgs)

    footer = cl.Message(
        content="**Submit** when every card is ✅ Approved or ❌ Rejected.",
        actions=build_footer_actions(iid),
    )
    await footer.send()
    cl.user_session.set(f"review_footer_{iid}", footer)


def _get_review_state(iid: str) -> dict | None:
    return cl.user_session.get(review_session_key(iid))


async def _refresh_review_summary(iid: str) -> None:
    state = _get_review_state(iid)
    if not state:
        return
    summary = cl.user_session.get(review_summary_key(iid))
    if summary:
        summary.content = format_review_summary(iid, state)
        await summary.update()


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
            msg.content = format_rec_card(i, r, state)
            msg.actions = build_rec_card_actions(iid, rec_id, i, state)
            await msg.update()
            break
    await _refresh_review_summary(iid)


@cl.action_callback("approve_rec")
async def approve_rec(action: cl.Action):
    iid = action.payload["id"]
    rec_id = action.payload["rec_id"]
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Review session expired — run a new incident.").send()
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
        await cl.Message(content="Review session expired — run a new incident.").send()
        return
    if rec_id in state["rejected"]:
        state["rejected"].remove(rec_id)
    else:
        state["rejected"].append(rec_id)
        if rec_id in state["approved"]:
            state["approved"].remove(rec_id)
    cl.user_session.set(review_session_key(iid), state)
    await _refresh_rec_card(iid, rec_id)


@cl.action_callback("edit_rec")
async def edit_rec(action: cl.Action):
    iid = action.payload["id"]
    rec_id = action.payload["rec_id"]
    idx = int(action.payload.get("idx", 0))
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Review session expired — run a new incident.").send()
        return
    original = state["modified"].get(rec_id)
    if not original:
        for r in state["recommendations"]:
            if r["id"] == rec_id:
                original = r.get("action", "")
                break
    res = await cl.AskUserMessage(
        content=(
            f"**Edit recommendation #{idx + 1}**\n\n"
            f"Current text:\n> {original}\n\n"
            "Enter the revised action (one or two sentences):"
        ),
        timeout=300,
    ).send()
    if not res or not res.get("output", "").strip():
        await cl.Message(content="Edit cancelled.").send()
        return
    state["modified"][rec_id] = res["output"].strip()
    if rec_id not in state["approved"]:
        state["approved"].append(rec_id)
    if rec_id in state["rejected"]:
        state["rejected"].remove(rec_id)
    cl.user_session.set(review_session_key(iid), state)
    await _refresh_rec_card(iid, rec_id)


@cl.action_callback("submit_review")
async def submit_review(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    state = _get_review_state(iid)
    if not state:
        await cl.Message(content="Review session expired.").send()
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
                f"**{len(pending)} recommendation(s) still pending.** "
                "Use ✅/❌ on each row, or Approve all / Reject all."
            )
        ).send()
        return
    resp = await _post_decision(
        iid,
        list(state["approved"]),
        list(state["rejected"]),
        None,
        dict(state["modified"]),
    )
    await cl.Message(content=_format_decision_result(resp)).send()


@cl.action_callback("approve_all")
async def approve_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    state = _get_review_state(iid)
    if state:
        state["approved"] = [r["id"] for r in state["recommendations"]]
        state["rejected"] = []
        cl.user_session.set(review_session_key(iid), state)
        for r in state["recommendations"]:
            await _refresh_rec_card(iid, r["id"])
    row = await _get_incident(iid)
    if not row:
        await cl.Message(content="Incident not found.").send()
        return
    rec_ids = [
        r["id"] for r in (row.get("incident_summary") or {}).get("ranked_recommendations", [])
    ]
    resp = await _post_decision(iid, rec_ids, [], None, {})
    await cl.Message(content=_format_decision_result(resp)).send()


@cl.action_callback("reject_all")
async def reject_all(action: cl.Action):
    iid = action.payload.get("id") or cl.user_session.get("incident_id")
    state = _get_review_state(iid)
    if state:
        state["rejected"] = [r["id"] for r in state["recommendations"]]
        state["approved"] = []
        cl.user_session.set(review_session_key(iid), state)
        for r in state["recommendations"]:
            await _refresh_rec_card(iid, r["id"])
    resp = await _post_decision(iid, [], ["*"], "Operator requested revision", {})
    await cl.Message(content=_format_decision_result(resp)).send()


def _format_decision_result(resp: dict) -> str:
    summary = resp.get("summary", {})
    return (
        f"**Decision recorded** — status `{resp.get('status', '?')}`\n\n"
        f"- Approved: {summary.get('approved_count', 0)}\n"
        f"- Rejected: {summary.get('rejected_count', 0)}\n"
        f"- Edited: {summary.get('modified_count', 0)}\n\n"
        f"_{resp.get('dispatch', 'SIMULATION')}_"
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
            },
        )
        r.raise_for_status()
        return r.json()
