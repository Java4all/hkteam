from __future__ import annotations

import re

from crisis.models.enums import Category, SeverityLevel
from crisis.models.schemas import Incident, IncidentReport, new_incident_id

_HINT_RULES: list[tuple[str, list[str]]] = [
    ("dam", ["dam", "levee", "breach"]),
    ("water_main", ["water main", "pipe burst", "broken pipe", "water pipe"]),
    ("hospital", ["hospital", "medical", "emr", "clinic"]),
    ("ransomware", ["ransomware", "cyber", "malware", "hacked", "breach"]),
    ("flood", ["flood", "flooding", "river", "overflow"]),
    ("terror", ["terrorist", "shooter", "active shooter", "bomb"]),
    ("power", ["power outage", "blackout", "electricity"]),
]

_CATEGORY_RULES: list[tuple[Category, list[str]]] = [
    (Category.PUBLIC_SAFETY, ["terror", "shooter", "bomb", "active shooter"]),
    (Category.CYBER, ["ransomware", "cyber", "malware", "hacked", "emr down"]),
    (Category.FLOOD, ["flood", "flooding", "river", "dam", "levee"]),
    (Category.UTILITIES, ["water main", "pipe", "utilities", "power outage", "gas leak"]),
    (Category.INFRASTRUCTURE, ["bridge", "road collapse", "tunnel", "infrastructure"]),
    (Category.PUBLIC_SERVICES, ["school", "transit", "bus", "service disruption"]),
]


def _extract_hints(text: str) -> list[str]:
    low = text.lower()
    hints: list[str] = []
    for name, keys in _HINT_RULES:
        if any(k in low for k in keys):
            hints.append(name)
    return hints


def _categories_from_text(text: str) -> tuple[list[Category], dict[str, float]]:
    low = text.lower()
    found: list[Category] = []
    confidence: dict[str, float] = {}
    for cat, keys in _CATEGORY_RULES:
        hits = sum(1 for k in keys if k in low)
        if hits:
            found.append(cat)
            confidence[cat.value] = min(0.95, 0.55 + 0.15 * hits)
    if not found:
        found = [Category.OTHER]
        confidence[Category.OTHER.value] = 0.5
    return found, confidence


def _severity(text: str, categories: list[Category]) -> SeverityLevel:
    low = text.lower()
    if any(w in low for w in ("critical", "terrorist", "active shooter", "city-wide", "mass casualty")):
        return SeverityLevel.CRITICAL
    if Category.PUBLIC_SAFETY in categories or "hospital" in low and "flood" in low:
        return SeverityLevel.CRITICAL
    if any(w in low for w in ("urgent", "major", "widespread", "evacuate")):
        return SeverityLevel.HIGH
    if any(w in low for w in ("minor", "localized", "small")):
        return SeverityLevel.LOW
    return SeverityLevel.MEDIUM


def classify_incident(report: IncidentReport) -> Incident:
    text = f"{report.description} {report.location}"
    categories, cat_conf = _categories_from_text(text)
    hints = _extract_hints(text)
    severity = _severity(text, categories)
    overall = max(cat_conf.values()) if cat_conf else 0.5
    return Incident(
        incident_id=new_incident_id(),
        description=report.description.strip(),
        location=report.location.strip(),
        categories=categories,
        severity=severity,
        confidence=overall,
        routing_hints=hints,
        original_report=report,
        category_confidence=cat_conf,
    )
