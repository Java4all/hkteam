"""Load per-agent workflow definitions from configs/agents/*.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from crisis.settings import settings

_AGENTS_DIR = settings.configs_dir / "agents"
_CACHE: dict[str, AgentConfig | None] = {}


@dataclass
class WorkflowAction:
    id: str
    type: str
    skill: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    input_from: list[str] | None = None
    output_schema: str | None = None
    rules: list[str] = field(default_factory=list)
    when: str | None = None
    emit: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDef:
    id: str
    description: str = ""
    inherits: str | None = None
    actions: list[WorkflowAction] = field(default_factory=list)


@dataclass
class WorkflowSelection:
    default: str = ""
    rules_file: str | None = None


@dataclass
class AgentConfig:
    agent_id: str
    role: str = ""
    display_name: str = ""
    workflow_selection: WorkflowSelection = field(default_factory=WorkflowSelection)
    workflows: dict[str, WorkflowDef] = field(default_factory=dict)
    rules_path: Path | None = None


def _parse_action(raw: dict[str, Any]) -> WorkflowAction:
    return WorkflowAction(
        id=str(raw["id"]),
        type=str(raw.get("type", "tool")),
        skill=raw.get("skill"),
        params=dict(raw.get("params") or {}),
        depends_on=list(raw.get("depends_on") or []),
        input_from=raw.get("input_from"),
        output_schema=raw.get("output_schema"),
        rules=list(raw.get("rules") or []),
        when=raw.get("when"),
        emit=dict(raw.get("emit") or {}),
    )


def _merge_workflow(parent: WorkflowDef, child: WorkflowDef) -> WorkflowDef:
    by_id = {a.id: a for a in parent.actions}
    for a in child.actions:
        by_id[a.id] = a
    return WorkflowDef(
        id=child.id,
        description=child.description or parent.description,
        inherits=child.inherits,
        actions=list(by_id.values()),
    )


def resolve_workflow(config: AgentConfig, workflow_id: str) -> WorkflowDef:
    if workflow_id not in config.workflows:
        raise KeyError(f"Unknown workflow {workflow_id!r} for agent {config.agent_id!r}")
    wf = config.workflows[workflow_id]
    if wf.inherits:
        parent = resolve_workflow(config, wf.inherits)
        return _merge_workflow(parent, wf)
    return wf


def load_agent_config(agent_id: str, *, reload: bool = False) -> AgentConfig | None:
    if not reload and agent_id in _CACHE:
        return _CACHE[agent_id]

    path = _AGENTS_DIR / f"{agent_id}.yaml"
    if not path.is_file():
        _CACHE[agent_id] = None
        return None

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sel_raw = data.get("workflow_selection") or {}
    selection = WorkflowSelection(
        default=str(sel_raw.get("default", "")),
        rules_file=sel_raw.get("rules_file"),
    )
    workflows: dict[str, WorkflowDef] = {}
    for wid, wraw in (data.get("workflows") or {}).items():
        workflows[wid] = WorkflowDef(
            id=wid,
            description=str((wraw or {}).get("description", "")),
            inherits=(wraw or {}).get("inherits"),
            actions=[_parse_action(a) for a in (wraw or {}).get("actions") or []],
        )

    rules_path = None
    if selection.rules_file:
        rules_path = _AGENTS_DIR / selection.rules_file

    config = AgentConfig(
        agent_id=str(data.get("agent_id", agent_id)),
        role=str(data.get("role", "")),
        display_name=str(data.get("display_name", "")),
        workflow_selection=selection,
        workflows=workflows,
        rules_path=rules_path,
    )
    _CACHE[agent_id] = config
    return config


def list_configured_agents() -> list[str]:
    return sorted(
        p.stem
        for p in _AGENTS_DIR.glob("*.yaml")
        if not p.name.endswith("_selector_rules.yaml")
    )


def clear_agent_config_cache() -> None:
    _CACHE.clear()
