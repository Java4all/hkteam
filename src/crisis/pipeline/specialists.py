"""Run specialist agents with pipeline stage progress (used from LangGraph node)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from crisis.agents.display import agent_display_name
from crisis.agents.specialist import run_specialist
from crisis.agents.workflow_overrides import apply_workflow_override
from crisis.graph.state import IncidentState
from crisis.llm.nvidia_health import nvidia_model_enablement_hint
from crisis.llm.registry import resolve_profile
from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import RouterHandoff, SpecialistOutput
from crisis.pipeline.events import PipelineStage, apply_stage, stages_for_api
from crisis.pipeline.helpers import (
    failed_specialist_output,
    handoff_from_state,
    llm_stage_detail,
)
from crisis.settings import settings

ProgressCallback = Callable[[dict[str, Any]], None]


def _emit(cb: ProgressCallback | None, payload: dict[str, Any]) -> None:
    if cb:
        cb(payload)


def run_specialists_with_progress(
    state: IncidentState,
    stages: list[PipelineStage],
    on_progress: ProgressCallback | None,
) -> tuple[IncidentState, list[PipelineStage]]:
    incident = state["incident"]
    routing = state["routing_decision"]
    handoff = handoff_from_state(incident, routing)
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
        stage_error = err or (
            None
            if out.status == SpecialistStatus.COMPLETE
            else "; ".join(out.check_notes) or None
        )
        if stage_error and out.status != SpecialistStatus.COMPLETE:
            try:
                model = resolve_profile(aid, "agent").model
            except Exception:
                model = None
            if "timed out" in (stage_error or "").lower():
                stage_error = (
                    f"{stage_error[:400]}\n\n→ NVIDIA cloud LLM timed out after "
                    f"{settings.crisis_specialist_llm_timeout:.0f}s. "
                    "Increase CRISIS_SPECIALIST_LLM_TIMEOUT in .env or check "
                    "integrate.api.nvidia.com latency."
                )
            hint = nvidia_model_enablement_hint(stage_error, model=model)
            if hint:
                stage_error = f"{stage_error[:400]}\n\n→ {hint}"
        stages = apply_stage(
            stages,
            f"specialist:{aid}",
            "complete" if out.status == SpecialistStatus.COMPLETE else "error",
            detail=f"{out.duration_ms}ms" if not err else "failed",
            error=stage_error,
        )
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

    def _emit_specialist_step(aid: str, detail: str) -> None:
        nonlocal stages
        stages = apply_stage(stages, f"specialist:{aid}", "running", detail=detail)
        _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})

    def _run_one(aid: str) -> tuple[str, SpecialistOutput, str | None]:
        stop_heartbeat = threading.Event()
        heartbeat_state = {"detail": llm_stage_detail(aid)}

        def heartbeat() -> None:
            t0 = time.perf_counter()
            while not stop_heartbeat.wait(12):
                elapsed = int(time.perf_counter() - t0)
                _emit_specialist_step(
                    aid, f"{heartbeat_state['detail']} · {elapsed}s elapsed"
                )

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()

        def on_step(detail: str) -> None:
            heartbeat_state["detail"] = detail
            _emit_specialist_step(aid, detail)

        try:
            agent_handoff = apply_workflow_override(handoff, aid)
            return aid, run_specialist(aid, agent_handoff, on_step=on_step), None
        except Exception as exc:
            return aid, failed_specialist_output(aid, "unknown", str(exc)), str(exc)
        finally:
            stop_heartbeat.set()

    if parallel:
        for aid in agents:
            stages = apply_stage(
                stages, f"specialist:{aid}", "running", detail=llm_stage_detail(aid)
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
                stages, f"specialist:{aid}", "running", detail=llm_stage_detail(aid)
            )
            _emit(on_progress, {"type": "stages", "stages": stages_for_api(stages)})
            aid, out, err = _run_one(aid)
            _record_result(aid, out, err)

    done = ",".join(outputs.keys())
    failed = [
        a
        for a, o in outputs.items()
        if o.status in (SpecialistStatus.FAILED, SpecialistStatus.TIMEOUT)
    ]
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
