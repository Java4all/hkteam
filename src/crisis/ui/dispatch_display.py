"""Format dispatch simulation for Chainlit (HTML; requires unsafe_allow_html)."""

from __future__ import annotations

from typing import Any

from crisis.ui.pipeline_display import SPINNER_FRAMES

_DISPATCH_FRAMES = SPINNER_FRAMES


def format_dispatch_in_progress(
    *,
    frame: int = 0,
    phase: str = "Recording operator decision",
    detail: str = "",
    completed: int = 0,
    total: int = 0,
) -> str:
    spinner = _DISPATCH_FRAMES[frame % len(_DISPATCH_FRAMES)]
    lines = [
        '<div class="crisis-dispatch-wrap crisis-dispatch-running">',
        f"### {spinner} Dispatch simulation — in progress",
        "",
        f"**{phase}**",
    ]
    if total > 0:
        pct = min(100, int(100 * completed / max(total, 1)))
        lines.extend(
            [
                "",
                '<div class="crisis-progress-wrap">',
                f'<div class="crisis-progress-meta"><strong>Outbound requests</strong> '
                f"{completed} of {total} · {pct}%</div>",
                '<div class="crisis-progress-track">',
                f'<div class="crisis-progress-fill" style="width:{pct}%;"></div>',
                "</div></div>",
            ]
        )
    if detail:
        lines.extend(["", f"_{detail}_"])
    lines.append("</div>")
    return "\n".join(lines)


def format_dispatch_summary_table(
    dispatch: dict[str, Any],
    *,
    decision_summary: dict[str, Any] | None = None,
) -> str:
    """Operator summary table for approved / rejected counts and dispatch rows."""
    entries = dispatch.get("entries") or []
    ds = decision_summary or {}
    lines = [
        '<div class="crisis-dispatch-summary">',
        "#### Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Approved | {ds.get('approved_count', len(entries))} |",
        f"| Rejected | {ds.get('rejected_count', 0)} |",
        f"| Dispatched (simulated) | {dispatch.get('dispatched_count', len(entries))} |",
        f"| Location | {dispatch.get('location') or '—'} |",
        "",
    ]
    if not entries:
        lines.append("_No approved recommendations — nothing dispatched._")
        lines.append("</div>")
        return "\n".join(lines)

    lines.extend(
        [
            "| Reference | Specialist | Target | Channel | Status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for e in entries:
        ref = e.get("reference", "—")
        specialist = e.get("specialist", "—")
        target = e.get("target_system", "—")
        channel = e.get("channel", "—")
        status = e.get("status", "—")
        lines.append(
            f"| `{ref}` | {specialist} | {target} | {channel} | {status} |"
        )
    lines.append("</div>")
    return "\n".join(lines)


def format_dispatch_simulation(
    dispatch: dict[str, Any] | None,
    *,
    decision_summary: dict[str, Any] | None = None,
) -> str:
    if not dispatch:
        return ""

    entries = dispatch.get("entries") or []
    simulated = dispatch.get("simulated", True)
    note = dispatch.get("note", "")
    location = dispatch.get("location") or "—"

    lines = [
        '<div class="crisis-dispatch-wrap">',
        "### ✅ Dispatch simulation complete",
        "",
    ]
    if simulated:
        lines.append("_No external systems contacted — preview of outbound requests._")
    else:
        lines.append("_Dispatch adapters queued — awaiting connector ACK._")
    lines.append("")
    lines.append(format_dispatch_summary_table(dispatch, decision_summary=decision_summary))
    lines.append("")

    if entries:
        lines.append("#### Request detail")
        lines.append("")
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
