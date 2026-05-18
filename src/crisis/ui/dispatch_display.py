"""Format dispatch simulation for Chainlit (HTML; requires unsafe_allow_html)."""

from __future__ import annotations

from typing import Any


def format_dispatch_simulation(dispatch: dict[str, Any] | None) -> str:
    if not dispatch:
        return ""

    entries = dispatch.get("entries") or []
    simulated = dispatch.get("simulated", True)
    note = dispatch.get("note", "")
    location = dispatch.get("location") or "—"

    lines = [
        '<div class="crisis-dispatch-wrap">',
        "## Dispatch simulation",
        "",
    ]
    if simulated:
        lines.append("_No external systems contacted — preview of outbound requests._")
    else:
        lines.append("_Dispatch adapters queued — awaiting connector ACK._")
    lines.append("")
    lines.append(f"**Location:** {location}")
    lines.append("")

    if not entries:
        lines.append("_No approved recommendations — nothing dispatched._")
        lines.append("</div>")
        return "\n".join(lines)

    for e in entries:
        ref = e.get("reference", "SIM-??????")
        specialist = e.get("specialist", "Specialist")
        target = e.get("target_system", "—")
        channel = e.get("channel", "—")
        status = e.get("status", "SIMULATED")
        action = e.get("action", "")
        lines.extend(
            [
                '<div class="crisis-dispatch-entry">',
                f'<div class="crisis-dispatch-ref">{ref}</div> '
                f'<span class="crisis-dispatch-meta">{specialist} → {target}</span>',
                f'<div class="crisis-dispatch-detail">'
                f"Channel: {channel} · Status: {status}</div>",
                f'<p class="crisis-dispatch-action">{action}</p>',
                "</div>",
                "",
            ]
        )

    if note:
        lines.append(f"_{note}_")
    lines.append("</div>")
    return "\n".join(lines)
