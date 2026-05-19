"""Execute the incident pipeline via LangGraph (Langfuse sees graph nodes)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from crisis.agents.display import agent_display_name
from crisis.graph.incident_graph import build_incident_graph
from crisis.graph.state import IncidentState
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import IncidentReport
from crisis.observability.langfuse import get_langfuse_config, langfuse_incident_session
from crisis.pipeline.events import (
    PipelineStage,
    apply_stage,
    initial_stages,
    stages_for_api,
    stages_to_trace,
)
from crisis.pipeline.progress_context import (
    bind_pipeline_progress,
    reset_pipeline_progress,
)
from crisis.routing.classifier import classify_incident

ProgressCallback = Callable[[dict[str, Any]], None]


def _emit(cb: ProgressCallback | None, payload: dict[str, Any]) -> None:
    if cb:
        cb(payload)


def _merge_state(state: IncidentState, partial: IncidentState) -> IncidentState:
    merged = dict(state)
    merged.update(partial)
    return merged  # type: ignore[return-value]


def _append_specialist_stages(
    stages: list[PipelineStage], selected: list[str]
) -> list[PipelineStage]:
    base = stages[:4]
    for aid in selected:
        base.append(
            PipelineStage(
                id=f"specialist:{aid}",
                label=f"Specialist: {agent_display_name(aid)}",
                agent_id=aid,
            )
        )
    return base


def _sync_stages_after_node(
    node_name: str,
    state: IncidentState,
    stages: list[PipelineStage],
    on_progress: ProgressCallback | None,
) -> list[PipelineStage]:
    if node_name == "intake":
        inc = state["incident"]
        stages = apply_stage(
            stages,
            "intake",
            "complete",
            detail=",".join(c.value for c in inc.categories),
        )
        stages = apply_stage(stages, "smart_route", "running")
    elif node_name == "smart_route":
        routing = state["routing_decision"]
        stages = apply_stage(
            stages,
            "smart_route",
            "complete",
            detail=f"{','.join(routing.selected)} ({routing.selection_mode})",
        )
        stages = _append_specialist_stages(stages, list(routing.selected))
        stages = apply_stage(stages, "run_specialists", "running")
    elif node_name == "run_specialists":
        # ctx.stages is the same list — specialists runner already updated specialist rows
        stages = apply_stage(stages, "aggregate", "running")
    elif node_name == "aggregate":
        failed_specialists = [
            aid
            for aid, out in (state.get("specialist_outputs") or {}).items()
            if out.status in (SpecialistStatus.FAILED, SpecialistStatus.TIMEOUT)
        ]
        agg_detail = (
            "briefing ready"
            if not failed_specialists
            else f"briefing ready · failed: {', '.join(failed_specialists)}"
        )
        stages = apply_stage(stages, "aggregate", "complete", detail=agg_detail)

    _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
    return stages


def _finalize_stages(state: IncidentState, stages: list[PipelineStage]) -> list[PipelineStage]:
    """Ensure UI/API stages match completed pipeline state (no stale pending/running)."""
    if state.get("incident"):
        inc = state["incident"]
        stages = apply_stage(
            stages,
            "intake",
            "complete",
            detail=",".join(c.value for c in inc.categories),
        )
    if state.get("routing_decision"):
        routing = state["routing_decision"]
        stages = apply_stage(
            stages,
            "smart_route",
            "complete",
            detail=f"{','.join(routing.selected)} ({routing.selection_mode})",
        )

    outputs = state.get("specialist_outputs") or {}
    for aid, out in outputs.items():
        sid = f"specialist:{aid}"
        st = "complete" if out.status == SpecialistStatus.COMPLETE else "error"
        detail = f"{out.duration_ms}ms" if out.status == SpecialistStatus.COMPLETE else "failed"
        err = None if out.status == SpecialistStatus.COMPLETE else "; ".join(out.check_notes) or "failed"
        stages = apply_stage(stages, sid, st, detail=detail, error=err)

    failed = [
        a
        for a, o in outputs.items()
        if o.status in (SpecialistStatus.FAILED, SpecialistStatus.TIMEOUT)
    ]
    rs_detail = "done:" + ",".join(outputs.keys()) if outputs else "done"
    if failed:
        rs_detail += f" failed:{','.join(failed)}"
    stages = apply_stage(
        stages,
        "run_specialists",
        "error" if failed and len(failed) == len(outputs) else "complete",
        detail=rs_detail,
        error=f"{len(failed)} specialist(s) failed" if failed else None,
    )

    if state.get("incident_summary"):
        agg_detail = (
            "briefing ready"
            if not failed
            else f"briefing ready · failed: {', '.join(failed)}"
        )
        stages = apply_stage(stages, "aggregate", "complete", detail=agg_detail)

    return stages


def run_incident_via_langgraph(
    report: IncidentReport,
    on_progress: ProgressCallback | None = None,
) -> IncidentState:
    """
    Run intake → route → specialists → aggregate through compiled LangGraph.

    Langfuse CallbackHandler on graph.stream() produces LangGraph node spans;
    LLM calls inside specialists remain BaseChatOpenAI children.
    """
    init: IncidentState = {"report": report, "trace": ["start"]}
    stages = initial_stages()
    stages = apply_stage(stages, "intake", "running")
    _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

    # Session id before stream (intake is rule-based; cheap to classify once)
    inc = classify_incident(report)
    graph = build_incident_graph()

    with langfuse_incident_session(inc.incident_id, tags=["incident-pipeline"]):
        lf_config = get_langfuse_config(session_id=inc.incident_id) or {}
        progress_token = bind_pipeline_progress(on_progress, stages)
        state: IncidentState = dict(init)
        try:
            for chunk in graph.stream(init, config=lf_config, stream_mode="updates"):
                for node_name, partial in chunk.items():
                    state = _merge_state(state, partial)
                    stages = _sync_stages_after_node(
                        node_name, state, stages, on_progress
                    )
        finally:
            reset_pipeline_progress(progress_token)

    stages = _finalize_stages(state, stages)
    _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
    state["pipeline_stages"] = stages_for_api(stages)  # type: ignore[typeddict-unknown-key]
    state["trace"] = list(state.get("trace") or []) + stages_to_trace(stages)[-5:]
    return state
