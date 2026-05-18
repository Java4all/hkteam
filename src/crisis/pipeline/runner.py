from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from crisis.agents.display import agent_display_name
from crisis.graph.incident_graph import (
    node_aggregate,
    node_intake,
    node_smart_route,
)
from crisis.graph.state import IncidentState
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import IncidentReport, RouterHandoff, SpecialistOutput
from crisis.observability.langfuse import flush_langfuse_traces, get_langfuse_config
from crisis.pipeline.events import (
    PipelineStage,
    apply_stage,
    initial_stages,
    stages_for_api,
    stages_to_trace,
)
from crisis.agents.specialist import run_specialist
from crisis.llm.registry import resolve_profile

ProgressCallback = Callable[[dict[str, Any]], None]


def _llm_stage_detail(agent_id: str) -> str:
    profile = resolve_profile(agent_id, "agent")
    model_short = profile.model.rsplit("/", 1)[-1]
    return f"{model_short} ({profile.llm_provider})"


def _handoff(incident, routing) -> RouterHandoff:
    return RouterHandoff(
        incident_id=incident.incident_id,
        categories=[c.value for c in incident.categories],
        severity=incident.severity,
        location=incident.location,
        description=incident.description,
        confidence=incident.confidence,
        routing_hints=incident.routing_hints,
        activated_reason=routing.rationale,
    )


def _failed_output(agent_id: str, workflow_id: str, error: str) -> SpecialistOutput:
    return SpecialistOutput(
        agent_id=agent_id,
        workflow_id=workflow_id or "unknown",
        workflow_selection_rationale="",
        recommendations=[],
        communication_drafts=[],
        evidence=[],
        checks_passed=False,
        check_notes=[error[:500]],
        confidence=0.0,
        status=SpecialistStatus.FAILED,
    )


def _emit(cb: ProgressCallback | None, payload: dict[str, Any]) -> None:
    if cb:
        cb(payload)


def _run_specialists_with_progress(
    state: IncidentState,
    stages: list[PipelineStage],
    on_progress: ProgressCallback | None,
) -> tuple[IncidentState, list[PipelineStage]]:
    incident = state["incident"]
    routing = state["routing_decision"]
    handoff = _handoff(incident, routing)
    outputs: dict[str, SpecialistOutput] = {}
    agents = list(routing.selected)
    parallel = routing.execution_mode == "parallel" and len(agents) > 1
    mode_label = "parallel" if parallel else "sequential"
    stages = apply_stage(
        stages, "run_specialists", "running", detail=f"{len(agents)} agent(s), {mode_label}"
    )
    _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

    def _record_result(aid: str, out: SpecialistOutput, err: str | None) -> None:
        nonlocal stages
        outputs[aid] = out
        stages = apply_stage(
            stages,
            f"specialist:{aid}",
            "complete" if out.status == SpecialistStatus.COMPLETE else "error",
            detail=f"{out.duration_ms}ms" if not err else "failed",
            error=err or (
                None
                if out.status == SpecialistStatus.COMPLETE
                else "; ".join(out.check_notes) or None
            ),
        )
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

    def _run_one(aid: str) -> tuple[str, SpecialistOutput, str | None]:
        try:
            return aid, run_specialist(aid, handoff), None
        except Exception as exc:
            return aid, _failed_output(aid, "unknown", str(exc)), str(exc)

    if parallel:
        for aid in agents:
            stages = apply_stage(
                stages, f"specialist:{aid}", "running", detail=_llm_stage_detail(aid)
            )
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
        with ThreadPoolExecutor(max_workers=min(len(agents), 4)) as pool:
            futures = {pool.submit(_run_one, aid): aid for aid in agents}
            for fut in as_completed(futures):
                aid, out, err = fut.result()
                _record_result(aid, out, err)
    else:
        for aid in agents:
            stages = apply_stage(
                stages, f"specialist:{aid}", "running", detail=_llm_stage_detail(aid)
            )
            _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
            aid, out, err = _run_one(aid)
            _record_result(aid, out, err)

    done = ",".join(outputs.keys())
    failed = [a for a, o in outputs.items() if o.status in (SpecialistStatus.FAILED, SpecialistStatus.TIMEOUT)]
    stages = apply_stage(
        stages,
        "run_specialists",
        "error" if failed and len(failed) == len(agents) else "complete",
        detail=f"done:{done}" + (f" failed:{','.join(failed)}" if failed else ""),
        error=f"{len(failed)} specialist(s) failed" if failed else None,
    )
    trace = list(state.get("trace") or [])
    trace.append(f"specialists_done:{done}")
    if failed:
        trace.append(f"specialists_failed:{','.join(failed)}")
    return {**state, "specialist_outputs": outputs, "trace": trace}, stages


def run_incident_pipeline(
    report: IncidentReport,
    on_progress: ProgressCallback | None = None,
) -> IncidentState:
    """Run the incident pipeline with optional progress callbacks."""
    get_langfuse_config(tags=["incident-pipeline"])
    init: IncidentState = {"report": report, "trace": ["start"]}
    stages = initial_stages()
    state = init

    try:
        stages = apply_stage(stages, "intake", "running")
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
        state = {**state, **node_intake(state)}
        inc = state["incident"]
        stages = apply_stage(
            stages,
            "intake",
            "complete",
            detail=",".join(c.value for c in inc.categories),
        )
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

        stages = apply_stage(stages, "smart_route", "running")
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
        state = {**state, **node_smart_route(state)}
        routing = state["routing_decision"]
        for sid, label in [("intake", "Classify incident"), ("smart_route", "Route to specialists")]:
            if sid == "smart_route":
                stages = apply_stage(
                    stages,
                    "smart_route",
                    "complete",
                    detail=f"{','.join(routing.selected)} ({routing.selection_mode})",
                )
        specialist_stages = [
            PipelineStage(
                id=f"specialist:{aid}",
                label=f"Specialist: {agent_display_name(aid)}",
                agent_id=aid,
            )
            for aid in routing.selected
        ]
        stages = stages[:4] + specialist_stages
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

        state, stages = _run_specialists_with_progress(state, stages, on_progress)

        stages = apply_stage(stages, "aggregate", "running")
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
        state = {**state, **node_aggregate(state)}
        stages = apply_stage(stages, "aggregate", "complete", detail="briefing ready")
        state["pipeline_stages"] = stages_for_api(stages)  # type: ignore[typeddict-unknown-key]
        state["trace"] = list(state.get("trace") or []) + stages_to_trace(stages)[-5:]
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
        return state
    except Exception as exc:
        stages = apply_stage(stages, "aggregate", "error", error=str(exc))
        _emit(
            on_progress,
            {
                "type": "error",
                "message": str(exc),
                "stages": stages_for_api(stages),
                "trace": state.get("trace", []),
            },
        )
        raise
    finally:
        flush_langfuse_traces()


def stream_incident_pipeline(report: IncidentReport) -> Iterator[str]:
    """SSE lines (data: {...}) for POST /incidents/stream."""
    import queue
    import threading

    from crisis.pipeline.serialize import incident_response
    from crisis.store import get_incident_store

    q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def on_progress(payload: dict[str, Any]) -> None:
        q.put(("event", payload))

    def worker() -> None:
        try:
            state = run_incident_pipeline(report, on_progress=on_progress)
            get_incident_store().save_pipeline_result(state)
            q.put(("saved", incident_response(state)))
        except Exception as exc:
            q.put(("error", str(exc)))

    threading.Thread(target=worker, daemon=True).start()
    while True:
        kind, payload = q.get()
        if kind == "event":
            yield f"data: {json.dumps(payload)}\n\n"
        elif kind == "saved":
            yield f"data: {json.dumps({'type': 'complete', **payload})}\n\n"
            break
        elif kind == "error":
            yield f"data: {json.dumps({'type': 'error', 'message': payload})}\n\n"
            break
