from __future__ import annotations

_STATUS_ICON = {
    "pending": "⏳",
    "running": "🔄",
    "complete": "✅",
    "error": "❌",
    "skipped": "⏭️",
}


def format_pipeline_stages(stages: list[dict]) -> str:
    if not stages:
        return "_No pipeline stages recorded._"
    lines = ["| Stage | Status | Detail |", "| --- | --- | --- |"]
    for s in stages:
        icon = _STATUS_ICON.get(s.get("status", "pending"), "•")
        label = s.get("label") or s.get("id", "")
        detail = (s.get("detail") or "").replace("|", "/")
        err = s.get("error")
        if err:
            detail = f"{detail} — **{err[:180]}**" if detail else f"**{err[:220]}**"
        lines.append(f"| {label} | {icon} {s.get('status', '')} | {detail or '—'} |")
    return "\n".join(lines)


def format_trace(trace: list[str]) -> str:
    if not trace:
        return "_No trace entries._"
    return "\n".join(f"- `{t}`" for t in trace)
