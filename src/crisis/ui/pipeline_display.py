from __future__ import annotations

# Smooth quarter-circle spinner (reads cleaner than Braille in tables)
SPINNER_FRAMES = ("◐", "◓", "◑", "◒")

_AGENT_ICON = {
    "flood": "🌊",
    "utilities": "💧",
    "infrastructure": "🌉",
    "comms": "📡",
    "cyber": "🛡️",
    "public_safety": "🚔",
    "public_services": "🏛️",
    "general": "🏙️",
}

_STATUS_ICON = {
    "pending": "○",
    "running": "◉",
    "complete": "✓",
    "error": "✕",
    "skipped": "—",
}


def _stage_icon(stage: dict) -> str:
    aid = stage.get("agent_id") or ""
    if aid and stage.get("id", "").startswith("specialist:"):
        return _AGENT_ICON.get(aid, "🤖")
    sid = stage.get("id", "")
    if sid == "intake":
        return "🔍"
    if sid == "smart_route":
        return "🧭"
    if sid == "run_specialists":
        return "🤖"
    if sid == "aggregate":
        return "📋"
    return "•"


def _progress_counts(stages: list[dict]) -> tuple[int, int, int, int]:
    total = len(stages) or 1
    complete = sum(1 for s in stages if s.get("status") == "complete")
    running = sum(1 for s in stages if s.get("status") == "running")
    errors = sum(1 for s in stages if s.get("status") == "error")
    return complete, total, running, errors


def _progress_bar(complete: int, total: int) -> str:
    """HTML progress bar — solid track + fill (no block characters)."""
    pct = min(100, max(0, int(100 * complete / max(total, 1))))
    return (
        '<div class="crisis-progress-wrap">'
        f'<div class="crisis-progress-meta"><strong>Progress</strong> '
        f"{complete} of {total} · {pct}%"
        '</div>'
        '<div class="crisis-progress-track">'
        f'<div class="crisis-progress-fill" style="width:{pct}%;"></div>'
        "</div></div>"
    )


def format_pipeline_progress(
    stages: list[dict],
    *,
    frame: int = 0,
    active: bool = False,
    headline: str | None = None,
) -> str:
    """Rich markdown for live pipeline updates (operator command center)."""
    if not stages:
        spinner = SPINNER_FRAMES[frame % len(SPINNER_FRAMES)] if active else "○"
        return (
            f"### {spinner} Crisis Response Command Center\n\n"
            "_Connecting to multi-agent orchestration…_"
        )

    complete, total, running, errors = _progress_counts(stages)
    spinner = SPINNER_FRAMES[frame % len(SPINNER_FRAMES)] if active and running else ""

    if active and running:
        title = f"### {spinner} Crisis Response Command Center"
        tagline = headline or "_NVIDIA NeMo specialists analyzing incident in real time…_"
    elif errors:
        title = "### ⚠️ Crisis Response Command Center"
        tagline = headline or "_Pipeline finished with errors — review stages below._"
    else:
        title = "### ✅ Crisis Response Command Center"
        tagline = headline or "_Multi-agent analysis complete — briefing ready for review._"

    lines = [
        title,
        "",
        f"> {tagline}",
        "",
        _progress_bar(complete, total),
        "",
    ]

    if active and running:
        active_names = [
            s.get("label", s.get("id", ""))
            for s in stages
            if s.get("status") == "running"
        ]
        if active_names:
            lines.append(f"**Active now:** {' · '.join(active_names[:4])}")
            lines.append("")

    lines.extend(["| | Stage | Status | Detail |", "| --- | --- | --- | --- |"])
    for s in stages:
        status = s.get("status", "pending")
        icon = _STATUS_ICON.get(status, "•")
        if status == "running" and active:
            icon = SPINNER_FRAMES[frame % len(SPINNER_FRAMES)]
        row_icon = _stage_icon(s)
        label = s.get("label") or s.get("id", "")
        detail = (s.get("detail") or "—").replace("|", "/")
        err = s.get("error")
        if err:
            detail = f"{detail} — **{err[:160]}**" if detail != "—" else f"**{err[:200]}**"
        lines.append(f"| {row_icon} | {label} | {icon} {status} | {detail} |")

    if not active and complete == total and not errors:
        lines.extend(
            [
                "",
                "✨ **Ready for operator review** — powered by multi-agent AI orchestration.",
            ]
        )
    return "\n".join(lines)


def format_pipeline_stages(stages: list[dict]) -> str:
    """Static table (final summary)."""
    return format_pipeline_progress(stages, active=False)


def format_trace(trace: list[str]) -> str:
    if not trace:
        return "_No trace entries._"
    return "\n".join(f"- `{t}`" for t in trace)
