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

from crisis.ui.pipeline_display import format_pipeline_stages, format_trace



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

        parts.append(f"HTTP {resp.status_code}")

        try:

            body = resp.json()

            if isinstance(body, dict):

                detail = body.get("detail", body)

                if isinstance(detail, dict):

                    if detail.get("message"):

                        parts.append(f"\n\n**Message:** {detail['message']}")

                    if detail.get("hint"):

                        parts.append(f"\n\n**Hint:** {detail['hint']}")

                    if detail.get("stage"):

                        parts.append(f"\n\n**Failed at:** `{detail['stage']}`")

                else:

                    parts.append(f"\n\n```\n{detail}\n```")

        except Exception:

            text = resp.text[:800] if resp.text else ""

            if text:

                parts.append(f"\n\n```\n{text}\n```")

    parts.append(

        "\n\nIf the trace stops after `smart_route`, specialists are likely failing "

        "(NVIDIA timeout, rate limit, or invalid model). Check `docker compose logs api` "

        "or run `make diagnose-nvidia` on the host."

    )

    return "".join(parts)





async def _run_incident_stream(

    client: httpx.AsyncClient, description: str, location: str

) -> tuple[dict | None, list[dict], str | None]:

    """Consume SSE from POST /incidents/stream; return result, stages, error message."""

    stages: list[dict] = []

    progress = cl.Message(content="### Pipeline progress\n\n_Starting…_")

    await progress.send()



    async with client.stream(

        "POST",

        f"{API}/incidents/stream",

        json={"description": description, "location": location},

        timeout=_PIPELINE_TIMEOUT,

    ) as resp:

        if resp.status_code >= 400:
            body = (await resp.aread()).decode("utf-8", errors="replace")[:800]
            return None, stages, f"HTTP {resp.status_code}: {body}"

        result: dict | None = None

        error_msg: str | None = None

        async for line in resp.aiter_lines():

            if not line or not line.startswith("data:"):

                continue

            try:

                payload = json.loads(line[5:].strip())

            except json.JSONDecodeError:

                continue

            if payload.get("type") == "stages":

                stages = payload.get("stages") or stages

                progress.content = (

                    "### Pipeline progress\n\n" + format_pipeline_stages(stages)

                )

                await progress.update()

            elif payload.get("type") == "complete":

                result = payload

                stages = payload.get("pipeline_stages") or stages

            elif payload.get("type") == "error":

                error_msg = payload.get("message", "Pipeline failed")

                stages = payload.get("stages") or stages

        if stages:

            progress.content = "### Pipeline progress\n\n" + format_pipeline_stages(stages)

            await progress.update()

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

            "**Smart City Crisis Management** (v1.0)\n\n"

            "Click a **starter** below, or paste an incident from `data/examples/*.txt` "

            "(last line = location).\n\n"

            "While the pipeline runs you will see **live stage updates** (classify → route → "

            "each specialist → briefing).\n\n"

            "Example:\n"

            "> Major water main rupture. Flooding on Oak Street.\n"

            "> Oak Street, Sector 7"

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



    data: dict | None = None

    stages: list[dict] = []



    async with httpx.AsyncClient(timeout=_PIPELINE_TIMEOUT) as client:

        try:

            data, stages, stream_err = await _run_incident_stream(client, description, location)

            if stream_err and not data:

                await cl.Message(

                    content=(

                        f"### Pipeline failed\n\n**{stream_err}**\n\n"

                        + format_pipeline_stages(stages)

                    )

                ).send()

                return

            if not data:

                data = await _run_incident_blocking(client, description, location)

                stages = data.get("pipeline_stages", [])

        except httpx.HTTPError as exc:

            await cl.Message(content=_format_api_error(exc)).send()

            return



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

            + " — briefing may be partial. See pipeline table for errors."

        )



    actions = [

        cl.Action(name="approve_all", payload={"id": iid}, label="Approve all recommendations"),

        cl.Action(name="reject_all", payload={"id": iid}, label="Reject (request revision)"),

    ]



    await cl.Message(

        content=(

            f"### Incident `{iid}`\n"

            f"**Severity:** {data.get('severity')} | **Categories:** {', '.join(data.get('categories', []))}\n"

            f"**Specialists activated:** {agents}\n"

            f"**Routing:** {routing.get('rationale', '')}{failed_note}\n\n"

            f"### Pipeline (final)\n{stage_table}\n\n"

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


