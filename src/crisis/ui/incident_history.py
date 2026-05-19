"""Incident history sidebar (Current + History tabs) for Chainlit."""

from __future__ import annotations

from typing import Any


def _status_badge(status: str) -> str:
    s = (status or "").upper()
    if s == "DISPATCHED":
        return "🟢 DISPATCHED"
    if s in ("AWAITING_HUMAN", "APPROVED"):
        return "🟡 " + s.replace("_", " ")
    if s == "ANALYZING":
        return "🔵 ANALYZING"
    if s == "REJECTED":
        return "🔴 REJECTED"
    return s.replace("_", " ")


def format_current_incident_panel(
    summary: dict[str, Any] | None, *, incident_id: str | None
) -> str:
    if not incident_id or not summary:
        return (
            '<div class="crisis-history-panel">'
            "<p><em>No active incident in this session.</em></p>"
            "<p>Submit a situation report or select a scenario chip to begin.</p>"
            "</div>"
        )
    cats = ", ".join(summary.get("categories") or []) or "—"
    lines = [
        '<div class="crisis-history-panel">',
        f"**`{incident_id}`**",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Status | {_status_badge(summary.get('status', ''))} |",
        f"| Severity | {summary.get('severity', '—')} |",
        f"| Categories | {cats} |",
        f"| Location | {summary.get('location', '—')} |",
        f"| Recommendations | {summary.get('recommendation_count', 0)} |",
        f"| Approved | {summary.get('approved_count', 0)} |",
        f"| Rejected | {summary.get('rejected_count', 0)} |",
        "",
        "</div>",
    ]
    return "\n".join(lines)


def format_history_table(
    items: list[dict[str, Any]], *, current_id: str | None = None
) -> str:
    if not items:
        return (
            '<div class="crisis-history-panel">'
            "<p><em>No incidents recorded yet.</em></p>"
            "</div>"
        )
    lines = [
        '<div class="crisis-history-panel">',
        "| Incident | Status | Severity | Location |",
        "| --- | --- | --- | --- |",
    ]
    for row in items:
        iid = row.get("incident_id", "—")
        marker = " **← current**" if current_id and iid == current_id else ""
        loc = (row.get("location") or "—")[:40]
        lines.append(
            f"| `{iid}`{marker} | {_status_badge(row.get('status', ''))} | "
            f"{row.get('severity', '—')} | {loc} |"
        )
    lines.append("</div>")
    return "\n".join(lines)


def format_incident_sidebar_html(
    *,
    current_id: str | None,
    current_summary: dict[str, Any] | None,
    history: list[dict[str, Any]],
) -> str:
    """HTML with Current / History tabs for the element sidebar."""
    current_html = format_current_incident_panel(current_summary, incident_id=current_id)
    history_html = format_history_table(history, current_id=current_id)
    return "\n".join(
        [
            '<div class="crisis-sidebar-tabs">',
            '<nav class="crisis-sidebar-tab-nav">',
            '<button type="button" class="crisis-tab active" data-crisis-tab="current">Current</button>',
            '<button type="button" class="crisis-tab" data-crisis-tab="history">History</button>',
            "</nav>",
            '<div class="crisis-tab-panel active" data-crisis-panel="current">',
            "### Current incident",
            "",
            current_html,
            "</div>",
            '<div class="crisis-tab-panel" data-crisis-panel="history" hidden>',
            "### Incident history",
            "",
            f"_Showing {len(history)} most recent incident(s)._",
            "",
            history_html,
            "</div>",
            "</div>",
        ]
    )
