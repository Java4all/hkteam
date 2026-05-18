from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StageStatus = Literal["pending", "running", "complete", "error", "skipped"]


class PipelineStage(BaseModel):
    id: str
    label: str
    status: StageStatus = "pending"
    detail: str = ""
    agent_id: str | None = None
    error: str | None = None


STAGE_ORDER = [
    ("intake", "Classify incident"),
    ("smart_route", "Route to specialists"),
    ("run_specialists", "Run specialist agents"),
    ("aggregate", "Build EOC briefing"),
]


def initial_stages(selected_agents: list[str] | None = None) -> list[PipelineStage]:
    stages = [PipelineStage(id=sid, label=label) for sid, label in STAGE_ORDER]
    if selected_agents:
        for aid in selected_agents:
            stages.append(
                PipelineStage(
                    id=f"specialist:{aid}",
                    label=f"Specialist: {aid}",
                    agent_id=aid,
                )
            )
    return stages


def stage_index(stages: list[PipelineStage], stage_id: str) -> int:
    for i, s in enumerate(stages):
        if s.id == stage_id:
            return i
    return -1


def apply_stage(
    stages: list[PipelineStage],
    stage_id: str,
    status: StageStatus,
    *,
    detail: str = "",
    error: str | None = None,
) -> list[PipelineStage]:
    idx = stage_index(stages, stage_id)
    if idx < 0:
        return stages
    updated = stages[idx].model_copy(
        update={"status": status, "detail": detail, "error": error}
    )
    out = list(stages)
    out[idx] = updated
    return out


def stages_to_trace(stages: list[PipelineStage]) -> list[str]:
    lines: list[str] = []
    for s in stages:
        if s.status == "pending":
            continue
        msg = f"{s.id}:{s.status}"
        if s.detail:
            msg += f" ({s.detail})"
        if s.error:
            msg += f" error={s.error[:200]}"
        lines.append(msg)
    return lines


def stages_for_api(stages: list[PipelineStage]) -> list[dict[str, Any]]:
    return [s.model_dump() for s in stages]
