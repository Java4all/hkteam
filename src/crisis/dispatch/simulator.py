"""Simulated outbound dispatch for approved recommendations (SIMULATION_MODE)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

from crisis.agents.display import agent_display_name
from crisis.agents.recommendations import agent_id_from_recommendation_id
from crisis.models.schemas import Recommendation

# specialist agent_id -> (target system label, integration channel)
_DISPATCH_TARGETS: dict[str, tuple[str, str]] = {
    "flood": ("Flood Control CAD", "CAD API"),
    "utilities": ("City Utilities OMS", "Work-order API"),
    "infrastructure": ("DOT Bridge & Roads", "Maintenance queue"),
    "comms": ("Public Alert Gateway", "IPAWS / SMS gateway"),
    "cyber": ("SOC / ITSM", "ServiceNow webhook"),
    "public_safety": ("Police–Fire CAD", "CAD API"),
}

_DEFAULT_TARGET = ("EOC coordination desk", "Internal task queue")


def _reference(incident_id: str, recommendation_id: str) -> str:
    digest = hashlib.sha256(f"{incident_id}:{recommendation_id}".encode()).hexdigest()[:6].upper()
    return f"SIM-{digest}"


def _truncate(text: str, max_len: int = 160) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def simulate_dispatch(
    *,
    incident_id: str,
    approved_ids: list[str],
    recommendations: list[Recommendation] | list[dict[str, Any]],
    modified: dict[str, str] | None = None,
    location: str = "",
    simulation_mode: bool = True,
) -> dict[str, Any]:
    """
    Build a dispatch log for approved recommendations.
    In simulation_mode, no external calls are made; entries are for UI/audit only.
    """
    modified = modified or {}
    by_id: dict[str, Recommendation | dict[str, Any]] = {}
    for rec in recommendations:
        rid = rec.id if isinstance(rec, Recommendation) else rec.get("id")
        if rid:
            by_id[str(rid)] = rec

    entries: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for rid in approved_ids:
        rec = by_id.get(rid)
        if not rec:
            continue
        if isinstance(rec, Recommendation):
            action = modified.get(rid) or rec.action
            priority = rec.priority
        else:
            action = modified.get(rid) or rec.get("action", "")
            priority = rec.get("priority", 3)

        agent_id = agent_id_from_recommendation_id(rid) or "unknown"
        target_system, channel = _DISPATCH_TARGETS.get(agent_id, _DEFAULT_TARGET)
        entries.append(
            {
                "reference": _reference(incident_id, rid),
                "recommendation_id": rid,
                "specialist": agent_display_name(agent_id),
                "target_system": target_system,
                "channel": channel,
                "priority": priority,
                "location": location or "—",
                "action": _truncate(action),
                "status": "ACKNOWLEDGED (simulated)" if simulation_mode else "QUEUED",
            }
        )

    return {
        "simulated": simulation_mode,
        "incident_id": incident_id,
        "location": location,
        "dispatched_at": now,
        "entries": entries,
        "dispatched_count": len(entries),
        "note": (
            "No external systems contacted — simulation only."
            if simulation_mode
            else "Dispatch requests queued for integration adapters."
        ),
    }
