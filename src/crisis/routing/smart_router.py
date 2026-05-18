from __future__ import annotations

from crisis.config.loader import load_routing_config
from crisis.models.enums import Category, SeverityLevel
from crisis.models.schemas import Incident, RoutingDecision

_AGENT_IDS = {
    Category.FLOOD: "flood",
    Category.INFRASTRUCTURE: "infrastructure",
    Category.CYBER: "cyber",
    Category.PUBLIC_SAFETY: "public_safety",
    Category.PUBLIC_SERVICES: "public_services",
    Category.UTILITIES: "utilities",
    Category.OTHER: "general",
}


def _candidates(incident: Incident, routing_cfg: dict) -> list[str]:
    cm = (routing_cfg.get("category_map") or {}).get("category_map") or {}
    agents: list[str] = []
    for cat in incident.categories:
        key = cat.value if isinstance(cat, Category) else str(cat)
        for a in cm.get(key, [_AGENT_IDS.get(Category(key), "general")]):
            if a not in agents:
                agents.append(a)
    sev_rules = (routing_cfg.get("category_map") or {}).get("always_for_severity") or {}
    for extra in sev_rules.get(incident.severity.value, []):
        if extra not in agents:
            agents.append(extra)
    if not agents:
        agents = ["general"]
    return agents


def _apply_dependency_rules(incident: Incident, candidates: list[str], routing_cfg: dict) -> list[str] | None:
    deps = (routing_cfg.get("dependencies") or {}).get("rules") or []
    cats = {c.value for c in incident.categories}
    hints = set(incident.routing_hints)
    for rule in deps:
        when = rule.get("when") or {}
        ok = True
        if "categories_include" in when:
            ok = ok and set(when["categories_include"]).issubset(cats)
        if "categories_exact" in when:
            ok = ok and set(when["categories_exact"]) == cats
        if "hints_include" in when:
            ok = ok and set(when["hints_include"]).issubset(hints)
        if not ok:
            continue
        selected = list(rule.get("activate") or candidates)
        for ex in rule.get("exclude") or []:
            if ex in selected:
                selected.remove(ex)
        return selected
    return None


def route_incident(incident: Incident) -> RoutingDecision:
    routing_cfg = load_routing_config()
    candidates = _candidates(incident, routing_cfg)
    rule_selected = _apply_dependency_rules(incident, candidates, routing_cfg)

    if incident.confidence < 0.6:
        primary = candidates[0] if candidates else "general"
        selected = [primary]
        mode = "minimal"
        rationale = "Low classification confidence — single primary agent."
    elif incident.severity == SeverityLevel.CRITICAL and len(incident.categories) >= 2:
        selected = candidates
        mode = "full"
        rationale = "CRITICAL multi-category incident — all candidate agents."
    elif rule_selected:
        selected = rule_selected
        mode = "targeted"
        rationale = "Dependency rule matched candidate set."
    elif len(candidates) == 1:
        selected = candidates
        mode = "minimal"
        rationale = "Single category — one specialist."
    else:
        selected = candidates[:3]
        mode = "targeted"
        rationale = "Multiple categories — targeted subset (capped at 3)."

    sr = (routing_cfg.get("category_map") or {}).get("smart_router") or {}
    max_agents = int(sr.get("max_parallel_agents", 4))
    selected = selected[:max_agents]
    deferred = [a for a in candidates if a not in selected]
    execution = "parallel" if incident.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) else "sequential"

    return RoutingDecision(
        incident_id=incident.incident_id,
        candidates=candidates,
        selected=selected,
        deferred=deferred,
        selection_mode=mode,
        execution_mode=execution,
        rationale=rationale,
        confidence=incident.confidence,
    )
