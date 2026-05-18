from __future__ import annotations


def agent_display_name(agent_id: str) -> str:
    """Human-readable specialist label for operator UI (e.g. flood → Flood)."""
    return agent_id.replace("_", " ").strip().title()


def format_agent_list(agent_ids: list[str] | dict[str, object]) -> str:
    """Comma-separated display names for UI."""
    if isinstance(agent_ids, dict):
        ids = list(agent_ids.keys())
    else:
        ids = list(agent_ids)
    return ", ".join(agent_display_name(aid) for aid in ids)
