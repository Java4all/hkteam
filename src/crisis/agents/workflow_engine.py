"""Execute per-agent workflows from configs/agents/*.yaml."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from crisis.agents.config_loader import AgentConfig, WorkflowAction, resolve_workflow
from crisis.agents.output_parse import parse_llm_output
from crisis.llm.registry import resolve_profile
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import RouterHandoff, SpecialistOutput
from crisis.skills.knowledge import enrich_agent_context
from crisis.skills.registry import run_skill

ChildRunner = Callable[[str, RouterHandoff, str | None, int], SpecialistOutput]


def _topo_sort(actions: list[WorkflowAction]) -> list[WorkflowAction]:
    by_id = {a.id: a for a in actions}
    ordered: list[WorkflowAction] = []
    seen: set[str] = set()

    def visit(aid: str) -> None:
        if aid in seen:
            return
        seen.add(aid)
        act = by_id.get(aid)
        if not act:
            return
        for dep in act.depends_on:
            visit(dep)
        ordered.append(act)

    for a in actions:
        visit(a.id)
    return ordered


def _rule_applies(when: str | None, handoff_ctx: dict[str, Any]) -> bool:
    if not when:
        return True
    when = when.strip()
    if "severity == CRITICAL" in when:
        return str(handoff_ctx.get("severity", "")).upper() == "CRITICAL"
    return True


def _run_single_action(
    action: WorkflowAction,
    *,
    agent_id: str,
    handoff_ctx: dict[str, Any],
    step_outputs: dict[str, str],
) -> tuple[str, str]:
    """Run one tool/llm action; returns (action_id, output_text)."""
    skill = action.skill or action.id
    params = dict(action.params)
    if action.input_from:
        params["input_from"] = action.input_from
    text = run_skill(
        skill,
        agent_id=agent_id,
        handoff_context=handoff_ctx,
        params=params,
        prior=step_outputs,
    )
    return action.id, text


def _format_subagent_output(child_id: str, out: SpecialistOutput) -> str:
    rec_lines = [f"- {r.text}" for r in out.recommendations[:5]]
    rec_block = "\n".join(rec_lines) if rec_lines else "(no recommendations)"
    return (
        f"## subagent:{child_id} (workflow={out.workflow_id})\n"
        f"### Recommendations\n{rec_block}"
    ).strip()


def run_agent_workflow(
    agent_id: str,
    workflow_id: str,
    handoff: RouterHandoff,
    config: AgentConfig,
    *,
    selection_rationale: str,
    depth: int = 0,
    child_runner: ChildRunner | None = None,
) -> SpecialistOutput:
    t0 = time.perf_counter()
    wf = resolve_workflow(config, workflow_id)
    handoff_ctx: dict[str, Any] = {
        "description": handoff.description,
        "location": handoff.location,
        "routing_hints": handoff.routing_hints,
        "severity": handoff.severity.value,
        "categories": handoff.categories,
        "workflow_id": workflow_id,
        "_depth": depth,
        "_parent_agent": agent_id,
    }
    step_outputs: dict[str, str] = {}
    check_notes: list[str] = []
    _, evidence_raw = enrich_agent_context(
        agent_id, handoff.description, handoff.location, handoff.routing_hints
    )

    for action in _topo_sort(wf.actions):
        if action.type == "rule":
            if _rule_applies(action.when, handoff_ctx) and action.emit:
                step_outputs[action.id] = str(action.emit)
                check_notes.append(f"rule:{action.id}:{action.emit}")
            continue

        if action.type == "critic":
            text = step_outputs.get("analyze") or ""
            if not text or len(text) < 80:
                check_notes.append(f"critic:{action.id}:output_too_short")
            continue

        if action.type == "parallel":
            steps_raw = action.params.get("steps") or []
            branches: list[WorkflowAction] = []
            for raw in steps_raw:
                if isinstance(raw, dict) and raw.get("id"):
                    branches.append(
                        WorkflowAction(
                            id=str(raw["id"]),
                            type=str(raw.get("type", "tool")),
                            skill=raw.get("skill"),
                            params=dict(raw.get("params") or {}),
                            input_from=raw.get("input_from"),
                        )
                    )
            if branches:
                with ThreadPoolExecutor(max_workers=min(4, len(branches))) as pool:
                    futures = [
                        pool.submit(
                            _run_single_action,
                            br,
                            agent_id=agent_id,
                            handoff_ctx=handoff_ctx,
                            step_outputs=dict(step_outputs),
                        )
                        for br in branches
                    ]
                    for fut in as_completed(futures):
                        aid, text = fut.result()
                        step_outputs[aid] = text
            else:
                check_notes.append(f"parallel:{action.id}:no_steps")
            continue

        if action.type == "subagent":
            child_id = str(action.params.get("agent_id", "")).strip()
            child_wf = action.params.get("workflow")
            if not child_id:
                check_notes.append(f"subagent:{action.id}:missing_agent_id")
                continue
            if not child_runner:
                check_notes.append(f"subagent:{action.id}:no_runner")
                continue
            child_out = child_runner(
                child_id,
                handoff,
                str(child_wf) if child_wf else None,
                depth + 1,
            )
            step_outputs[action.id] = _format_subagent_output(child_id, child_out)
            check_notes.append(f"subagent:{action.id}:{child_id}:{child_out.workflow_id}")
            continue

        if action.type == "nat_workflow":
            nat_name = action.params.get("workflow") or action.params.get("name") or "default"
            step_outputs[action.id] = (
                f"## nat_workflow:{nat_name}\n"
                "(NeMo Agent Toolkit step — configure configs/nat/ and wire runner in a future release.)"
            )
            continue

        if action.type in ("tool", "llm"):
            aid, text = _run_single_action(
                action,
                agent_id=agent_id,
                handoff_ctx=handoff_ctx,
                step_outputs=step_outputs,
            )
            step_outputs[aid] = text
            continue

        check_notes.append(f"skipped_action_type:{action.type}")

    llm_text = step_outputs.get("analyze") or "\n\n".join(step_outputs.values())
    out = parse_llm_output(agent_id, workflow_id, llm_text, evidence_raw)
    out.workflow_selection_rationale = selection_rationale
    out.duration_ms = int((time.perf_counter() - t0) * 1000)
    profile = resolve_profile(agent_id, "agent")
    out.llm_profile = profile.profile_id
    out.llm_model = profile.model
    out.llm_provider = profile.llm_provider
    if check_notes and not out.check_notes:
        out.check_notes = check_notes
    if any("critic" in n for n in check_notes):
        out.checks_passed = False
    out.status = SpecialistStatus.COMPLETE
    return out
