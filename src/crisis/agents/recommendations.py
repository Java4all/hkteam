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


def extract_recommendations_section(text: str) -> str:
    """Return markdown under ## Recommendations until the next ## heading."""
    match = re.search(r"##\s*Recommendations\b", text, re.I)
    if not match:
        return text
    rest = text[match.end() :]
    end = re.search(r"\n##\s+\S", rest)
    return rest[: end.start()] if end else rest


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


def parse_recommendation_bullets(text: str, *, max_items: int = 5) -> list[str]:
    """Extract actionable recommendation lines from specialist LLM markdown."""
    section = extract_recommendations_section(text)
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
            break
    return actions


def agent_id_from_recommendation_id(rec_id: str) -> str | None:
    m = re.match(r"rec-([^-]+)-\d+", rec_id)
    return m.group(1) if m else None
