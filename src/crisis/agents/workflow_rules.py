"""Evaluate workflow_selector rules from configs/agents/*_selector_rules.yaml."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from crisis.models.enums import SeverityLevel
from crisis.models.schemas import RouterHandoff


def _load_rules(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _hint_match(handoff: RouterHandoff, tokens: list[str]) -> bool:
    hay = " ".join(
        [
            handoff.description.lower(),
            handoff.location.lower(),
            " ".join(handoff.routing_hints).lower(),
        ]
    )
    return any(t.lower() in hay for t in tokens)


def evaluate_workflow_rules(
    handoff: RouterHandoff,
    rules_path: Path | None,
    *,
    default_workflow: str,
    allowed: list[str] | None = None,
) -> tuple[str, str]:
    if handoff.workflow_override:
        wf = handoff.workflow_override
        if allowed and wf not in allowed:
            return default_workflow, f"override_invalid:{wf}"
        return wf, "workflow_override"

    if not rules_path or not rules_path.is_file():
        return default_workflow, "default"

    doc = _load_rules(rules_path)
    allowed = allowed or list(doc.get("llm_fallback", {}).get("allowed_workflows") or [])

    for rule in doc.get("rules") or []:
        cond = str(rule.get("if", "")).strip()
        then = str(rule.get("then", "")).strip()
        if not cond or not then:
            continue

        if "workflow_override is not null" in cond:
            continue

        m = re.match(r"any\(hints,\s*\[(.+)\]\)", cond)
        if m:
            tokens = [t.strip().strip("'\"") for t in m.group(1).split(",")]
            if _hint_match(handoff, tokens):
                target = then.strip("${}")
                return target, f"rule:{cond[:40]}"

        m = re.match(r"severity\s*==\s*(\w+)", cond)
        if m:
            sev = m.group(1).upper()
            if handoff.severity == SeverityLevel[sev]:
                return then, f"rule:severity=={sev}"

        m = re.match(r"severity\s+in\s+\[(.+)\]", cond)
        if m:
            levels = {s.strip().strip("'\"").upper() for s in m.group(1).split(",")}
            if handoff.severity.value.upper() in levels:
                return then, f"rule:severity_in"

    default = str(doc.get("default") or default_workflow)
    return default, "rules_default"
