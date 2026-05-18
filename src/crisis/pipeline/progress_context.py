"""Thread-local progress hooks while LangGraph runs specialist node."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from collections.abc import Callable
from typing import Any

from crisis.pipeline.events import PipelineStage

ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class PipelineProgressContext:
    on_progress: Any | None
    stages: list[PipelineStage]


_ctx: ContextVar[PipelineProgressContext | None] = ContextVar(
    "pipeline_progress_ctx", default=None
)


def bind_pipeline_progress(
    on_progress: ProgressCallback | None, stages: list[PipelineStage]
) -> object:
    return _ctx.set(PipelineProgressContext(on_progress=on_progress, stages=stages))


def reset_pipeline_progress(token: object) -> None:
    _ctx.reset(token)


def get_pipeline_progress() -> PipelineProgressContext | None:
    return _ctx.get()
