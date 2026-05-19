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
_STATUS_OBSERVATION = re.compile(
    r"\b("
    r"degraded|unconfirmed|downtime procedures|workflows degraded|"
    r"possible data exfiltration|some departments on"
    r")\b",
    re.I,
)
_ACTION_VERB = re.compile(
    r"\b("
    r"activate|preserve|refrain|deploy|isolate|notify|coordinate|implement|"
    r"establish|shut|close|evacuate|dispatch|contact|engage|restore|contain|"
    r"do not pay|avoid paying"
    r")\b",
    re.I,
)
_LABEL_COLON = re.compile(
    r"^(\*\*)?([^*\n:]+?)(\*\*)?\s*:\s*(.+)$",
)

_RECOMMENDATIONS_HEADING = re.compile(
    r"^#{1,3}\s*Recommendations\b|^Recommendations\s*$",
    re.I | re.M,
)
_NEXT_TOP_SECTION = re.compile(r"\n##\s+\S", re.M)
def extract_recommendations_section(text: str) -> str:
    """Return markdown under a Recommendations heading until the next ## section."""
    match = _RECOMMENDATIONS_HEADING.search(text)
    if not match:
        return ""
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
    line = re.sub(r"\*\*", "", line)
    line = re.sub(
        r"^(immediate|long[- ]?term|short[- ]?term)\s+actions?\s*:\s*",
        "",
        line,
        flags=re.I,
    ).strip()
    return line


def normalize_recommendation_key(action: str) -> str:
    """Stable dedup key for review cards (handles Label: description variants)."""
    text = clean_recommendation_action(action)
    if ":" in text:
        _label, _, right = text.partition(":")
        right = right.strip()
        left = _label.strip()
        if right and len(right) >= 12:
            text = right
        elif len(left) >= 12:
            text = left
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()[:160]


def is_status_observation_line(line: str) -> bool:
    cleaned = clean_recommendation_action(line)
    if _ACTION_VERB.search(cleaned):
        return False
    if _STATUS_OBSERVATION.search(cleaned):
        return True
    if re.match(
        r"^(clinical workflows|some departments|possible data)\b",
        cleaned,
        re.I,
    ):
        return True
    return False


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
    if is_status_observation_line(cleaned):
        return False
    return True


def _line_to_action(raw: str) -> str | None:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return None
    m = _LABEL_COLON.match(stripped)
    if m:
        label = clean_recommendation_action(m.group(2))
        body = clean_recommendation_action(m.group(4))
        if body and len(body) >= 12:
            if label and len(label) >= 8 and label.lower() not in body.lower()[:50]:
                candidate = f"{label}: {body}"
            else:
                candidate = body
        elif label and len(label) >= 12:
            candidate = label
        else:
            candidate = f"{label}: {body}".strip(": ")
        if is_valid_recommendation_line(candidate):
            return clean_recommendation_action(candidate)
        return None
    if not is_valid_recommendation_line(stripped):
        return None
    return clean_recommendation_action(stripped)


def _is_duplicate_action(key: str, seen: set[str]) -> bool:
    if key in seen:
        return True
    for existing in seen:
        if len(key) < 18 or len(existing) < 18:
            continue
        if key in existing or existing in key:
            return True
    return False


def _collect_recommendation_lines(section: str, *, max_items: int) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def add_action(action: str) -> bool:
        key = normalize_recommendation_key(action)
        if not key or _is_duplicate_action(key, seen):
            return False
        seen.add(key)
        actions.append(action)
        return len(actions) >= max_items

    for raw in re.findall(r"^[-*]\s+(.+)$", section, re.M):
        action = _line_to_action(raw)
        if action and add_action(action):
            return actions

    for raw in re.findall(r"^\d+\.\s+(.+)$", section, re.M):
        action = _line_to_action(raw)
        if action and add_action(action):
            return actions

    for line in section.splitlines():
        action = _line_to_action(line)
        if action and add_action(action):
            return actions

    return actions


def parse_recommendation_bullets(text: str, *, max_items: int = 5) -> list[str]:
    """Extract actionable recommendation lines from specialist or EOC markdown."""
    section = extract_recommendations_section(text)
    if not section.strip():
        return []
    return _collect_recommendation_lines(section, max_items=max_items)


def recommendations_from_narrative(
    narrative: str,
    *,
    agent_id: str = "eoc",
    max_items: int = 12,
) -> list[dict]:
    """Build review-ready recommendation dicts from EOC briefing markdown."""
    bullets = parse_recommendation_bullets(narrative, max_items=max_items)
    seen: set[str] = set()
    recs: list[dict] = []
    for action in bullets:
        key = normalize_recommendation_key(action)
        if not key or _is_duplicate_action(key, seen):
            continue
        seen.add(key)
        recs.append(
            {
                "id": f"rec-{agent_id}-{len(recs) + 1}",
                "priority": min(5, len(recs) + 1),
                "action": action,
                "rationale": "From EOC briefing",
                "evidence_ids": [],
            }
        )
        if len(recs) >= max_items:
            break
    return recs


def agent_id_from_recommendation_id(rec_id: str) -> str | None:
    m = re.match(r"rec-([^-]+)-\d+", rec_id)
    return m.group(1) if m else None
