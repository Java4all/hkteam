from __future__ import annotations

import re

_SECTION_HEADER = re.compile(
    r"^(\[\d+\]\s*)?"
    r"(immediate|long[- ]?term|short[- ]?term|follow[- ]?up)\s+actions?\s*:?\s*$",
    re.I,
)
_LEADING_INDEX = re.compile(r"^\[\d+\]\s*")
_NARRATIVE_START = re.compile(
    r"^(the incident|this incident|the proximity|the situation|it is important that)\b",
    re.I,
)


_RECOMMENDATIONS_HEADING = re.compile(r"^#{1,3}\s*Recommendations\b", re.I | re.M)
_NEXT_TOP_SECTION = re.compile(r"\n##\s+\S", re.M)


def extract_recommendations_section(text: str) -> str:
    """Return markdown under a Recommendations heading until the next section."""
    match = _RECOMMENDATIONS_HEADING.search(text)
    if not match:
        return text
    rest = text[match.end() :]
    end = _NEXT_TOP_SECTION.search(rest)
    return rest[: end.start()] if end else rest


def strip_recommendations_from_narrative(narrative: str) -> str:
    """Remove the Recommendations section (interactive review shows them separately)."""
    match = _RECOMMENDATIONS_HEADING.search(narrative)
    if not match:
        return narrative.strip()
    before = narrative[: match.start()].rstrip()
    rest = narrative[match.end() :]
    end = _NEXT_TOP_SECTION.search(rest)
    after = rest[end.start() :].lstrip() if end else ""
    if before and after:
        return f"{before}\n\n{after}".strip()
    return (before or after).strip()


def clean_recommendation_action(line: str) -> str:
    line = _LEADING_INDEX.sub("", line.strip())
    line = re.sub(
        r"^(immediate|long[- ]?term|short[- ]?term)\s+actions?\s*:\s*",
        "",
        line,
        flags=re.I,
    ).strip()
    return line


def is_valid_recommendation_line(line: str) -> bool:
    stripped = line.strip()
    if len(stripped) < 12:
        return False
    if _SECTION_HEADER.match(stripped):
        return False
    if stripped.endswith(":") and len(stripped) < 60:
        return False
    cleaned = clean_recommendation_action(stripped)
    if len(cleaned) < 12:
        return False
    if _NARRATIVE_START.match(cleaned):
        return False
    return True


def _collect_recommendation_lines(section: str, *, max_items: int) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"^[-*]\s+(.+)$", section, re.M):
        if not is_valid_recommendation_line(raw):
            continue
        action = clean_recommendation_action(raw)
        key = re.sub(r"\s+", " ", action.lower())[:100]
        if key in seen:
            continue
        seen.add(key)
        actions.append(action)
        if len(actions) >= max_items:
            return actions
    for raw in re.findall(r"^\d+\.\s+(.+)$", section, re.M):
        if not is_valid_recommendation_line(raw):
            continue
        action = clean_recommendation_action(raw)
        key = re.sub(r"\s+", " ", action.lower())[:100]
        if key in seen:
            continue
        seen.add(key)
        actions.append(action)
        if len(actions) >= max_items:
            break
    return actions


def parse_recommendation_bullets(text: str, *, max_items: int = 5) -> list[str]:
    """Extract actionable recommendation lines from specialist or EOC markdown."""
    section = extract_recommendations_section(text)
    return _collect_recommendation_lines(section, max_items=max_items)


def recommendations_from_narrative(
    narrative: str,
    *,
    agent_id: str = "eoc",
    max_items: int = 12,
) -> list[dict]:
    """Build review-ready recommendation dicts from EOC briefing markdown."""
    bullets = parse_recommendation_bullets(narrative, max_items=max_items)
    return [
        {
            "id": f"rec-{agent_id}-{i + 1}",
            "priority": min(5, i + 1),
            "action": action,
            "rationale": "From EOC briefing",
            "evidence_ids": [],
        }
        for i, action in enumerate(bullets)
    ]


def agent_id_from_recommendation_id(rec_id: str) -> str | None:
    m = re.match(r"rec-([^-]+)-\d+", rec_id)
    return m.group(1) if m else None
