"""Animated dispatch simulation progress in Chainlit."""

from __future__ import annotations

import asyncio
from typing import Any

import chainlit as cl

from crisis.ui.dispatch_display import (
    format_dispatch_in_progress,
    format_dispatch_simulation,
)


class DispatchProgressUI:
    """Live-updating dispatch simulation message."""

    def __init__(self) -> None:
        self.message: cl.Message | None = None
        self._frame = 0
        self._active = False
        self._task: asyncio.Task | None = None

    async def start(self, *, total: int = 0) -> None:
        self._total = total
        self._completed = 0
        self._phase = "Recording operator decision"
        self._detail = ""
        self._active = True
        self.message = cl.Message(
            content=format_dispatch_in_progress(
                frame=0,
                phase=self._phase,
                detail=self._detail,
                completed=0,
                total=total,
            ),
            tags=["crisis-dispatch"],
        )
        await self.message.send()
        self._task = asyncio.create_task(self._animate())

    async def set_phase(
        self, phase: str, *, detail: str = "", completed: int | None = None
    ) -> None:
        self._phase = phase
        self._detail = detail
        if completed is not None:
            self._completed = completed
        await self._render()

    async def finish(
        self,
        dispatch: dict[str, Any],
        *,
        decision_summary: dict[str, Any] | None = None,
    ) -> None:
        self._active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self.message:
            self.message.content = format_dispatch_simulation(
                dispatch, decision_summary=decision_summary
            )
            await self.message.update()

    async def _animate(self) -> None:
        try:
            while self._active:
                self._frame += 1
                await self._render()
                await asyncio.sleep(0.4)
        except asyncio.CancelledError:
            pass

    async def _render(self) -> None:
        if not self.message:
            return
        self.message.content = format_dispatch_in_progress(
            frame=self._frame,
            phase=self._phase,
            detail=self._detail,
            completed=self._completed,
            total=getattr(self, "_total", 0),
        )
        await self.message.update()


async def animate_dispatch_reveal(
    ui: DispatchProgressUI,
    *,
    approved_ids: list[str],
    post_fn,
) -> dict[str, Any]:
    """
    Show in-progress UI, call API, then step through outbound requests before final table.
    ``post_fn`` is an async callable returning the decision API response dict.
    """
    total = len(approved_ids)
    await ui.start(total=total or 1)
    await ui.set_phase("Recording operator decision", detail="Updating incident status…")
    resp = await post_fn()
    dispatch = resp.get("dispatch_simulation") or {}
    entries = dispatch.get("entries") or []

    if not entries and total:
        await ui.set_phase(
            "Simulating dispatch",
            detail=f"Processing {total} approved recommendation(s)…",
            completed=0,
        )
        await asyncio.sleep(0.5)

    for i, entry in enumerate(entries, start=1):
        ref = entry.get("reference", "SIM-??????")
        target = entry.get("target_system", "—")
        await ui.set_phase(
            "Dispatching to target systems",
            detail=f"`{ref}` → {target}",
            completed=i,
        )
        await asyncio.sleep(0.35)

    if not entries:
        await ui.set_phase("Finalizing simulation", completed=total, detail="Complete")
        await asyncio.sleep(0.25)

    await ui.finish(dispatch, decision_summary=resp.get("summary"))
    return resp
