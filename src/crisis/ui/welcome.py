"""Welcome / help copy for Chainlit (landing readme + optional chat message)."""

from __future__ import annotations

_HELP_BODY = """
<p>This workspace ingests situation reports, coordinates cross-domain specialist
analysis, and produces a consolidated briefing for command staff. Decisions you
record here are retained for audit and after-action review.</p>

<p class="crisis-welcome-section">Submit an incident</p>
<p>Enter a situation report in the message field below. Place the
<strong>affected location</strong> on the final line (address, intersection,
facility, or operational area).</p>

<p class="crisis-welcome-section">Command review</p>
<p>When analysis completes, validate each recommendation with
<strong>Approve</strong> or <strong>Reject</strong> on each item, then select
<strong>Submit</strong> to run the dispatch simulation and finalize the
incident package.</p>

""".strip()


def format_welcome_message(*, include_help: bool = True) -> str:
    """Title + subtitle; optional collapsible help (HTML, requires unsafe_allow_html)."""
    lines = [
        '<div class="crisis-welcome">',
        '<p class="crisis-welcome-main">Smart City Crisis Management</p>',
        '<p class="crisis-welcome-details">',
        "Emergency Operations Center — Incident Analysis Console",
        "</p>",
    ]
    if include_help:
        lines.extend(
            [
                '<details class="crisis-help">',
                '<summary class="crisis-help-trigger">',
                '<span class="crisis-help-icon" aria-hidden="true">?</span>',
                " Help",
                "</summary>",
                f'<div class="crisis-help-body">{_HELP_BODY}</div>',
                "</details>",
            ]
        )
    lines.append("</div>")
    return "\n".join(lines)
