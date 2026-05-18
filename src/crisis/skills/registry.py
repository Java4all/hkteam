"""Skill handlers invoked by the YAML workflow engine."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from crisis.llm.registry import get_llm
from crisis.skills.knowledge import enrich_agent_context


def run_skill(
    skill: str,
    *,
    agent_id: str,
    handoff_context: dict[str, Any],
    params: dict[str, Any],
    prior: dict[str, str],
) -> str:
    handler = _HANDLERS.get(skill)
    if not handler:
        return f"(skill {skill!r} not registered — skipped)"
    return handler(
        agent_id=agent_id,
        handoff_context=handoff_context,
        params=params,
        prior=prior,
    )


def _playbook_rag(
    *,
    agent_id: str,
    handoff_context: dict[str, Any],
    params: dict[str, Any],
    prior: dict[str, str],
) -> str:
    tags = params.get("tags") or [agent_id]
    blob, _ = enrich_agent_context(
        agent_id,
        handoff_context["description"],
        handoff_context["location"],
        list(handoff_context.get("routing_hints") or []),
    )
    return f"## playbook_rag (tags={tags})\n{blob[:3500]}"


def _weather_api(**_kwargs: Any) -> str:
    loc = _kwargs["handoff_context"].get("location", "unknown")
    return (
        f"## weather_api (simulated)\n"
        f"Location {loc}: elevated precipitation risk next 6h; monitor NWS advisories."
    )


def _flood_zone_gis(**_kwargs: Any) -> str:
    loc = _kwargs["handoff_context"].get("location", "unknown")
    return f"## flood_zone_gis (simulated)\nRiverside / low-lying zones near {loc} flagged on GIS layer."


def _evacuation_routes(**_kwargs: Any) -> str:
    return "## evacuation_routes (simulated)\nPrimary evac corridors: northbound arterials; avoid underpasses."


def _draft_recommendation(
    *,
    agent_id: str,
    handoff_context: dict[str, Any],
    params: dict[str, Any],
    prior: dict[str, str],
) -> str:
    input_from = params.get("input_from")
    parts: list[str] = []
    if input_from:
        for key in input_from:
            if key in prior:
                parts.append(prior[key])
    else:
        parts.extend(prior.values())
    context = "\n\n".join(parts) if parts else "(no prior steps)"

    llm = get_llm(agent_id, "agent")
    workflow_id = handoff_context.get("workflow_id", "unknown")
    sys = SystemMessage(
        content=(
            f"You are the {agent_id} specialist for a city crisis EOC. "
            "Use ONLY the context provided. Output Markdown with:\n"
            "## Summary\n## Recommendations\n"
            "Under Recommendations, list 3–5 bullet lines. Each bullet must be one "
            "clear, imperative action.\n## Communication\n"
        )
    )
    human = HumanMessage(
        content=(
            f"Workflow: {workflow_id}\n"
            f"Severity: {handoff_context.get('severity')}\n"
            f"Categories: {', '.join(handoff_context.get('categories') or [])}\n\n"
            f"Context:\n{context}"
        )
    )
    resp = llm.invoke([sys, human])
    return getattr(resp, "content", str(resp))


_HANDLERS = {
    "playbook_rag": _playbook_rag,
    "weather_api": _weather_api,
    "flood_zone_gis": _flood_zone_gis,
    "evacuation_routes": _evacuation_routes,
    "draft_recommendation": _draft_recommendation,
}
