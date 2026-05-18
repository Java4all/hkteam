from __future__ import annotations

import asyncio

import chainlit as cl

from crisis.ui.pipeline_display import format_pipeline_progress


class PipelineProgressUI:
    """Live-updating progress message with rolling spinner frames."""

    def __init__(self) -> None:
        self.message: cl.Message | None = None
        self.stages: list[dict] = []
        self._frame = 0
        self._active = False
        self._task: asyncio.Task | None = None

    async def start(self, headline: str | None = None) -> None:
        self._headline = headline
        self._active = True
        self.message = cl.Message(
            content=format_pipeline_progress(
                [], frame=0, active=True, headline=headline
            )
        )
        await self.message.send()
        self._task = asyncio.create_task(self._animate())

    async def set_stages(self, stages: list[dict]) -> None:
        self.stages = stages
        await self._render()

    async def finish(self, stages: list[dict], *, success: bool = True) -> None:
        self.stages = stages
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        headline = (
            "_Multi-agent analysis complete — briefing ready for review._"
            if success
            else "_Pipeline stopped — see errors below._"
        )
        await self._render(active=False, headline=headline)

    async def _animate(self) -> None:
        try:
            while self._active:
                self._frame += 1
                await self._render(active=True)
                await asyncio.sleep(0.4)
        except asyncio.CancelledError:
            pass

    async def _render(self, *, active: bool | None = None, headline: str | None = None) -> None:
        if not self.message:
            return
        is_active = self._active if active is None else active
        self.message.content = format_pipeline_progress(
            self.stages,
            frame=self._frame,
            active=is_active,
            headline=headline or getattr(self, "_headline", None),
        )
        await self.message.update()
