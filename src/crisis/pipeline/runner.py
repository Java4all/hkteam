from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any

from crisis.graph.state import IncidentState
from crisis.models.schemas import IncidentReport
from crisis.pipeline.graph_runner import run_incident_via_langgraph
from crisis.pipeline.helpers import failed_specialist_output, handoff_from_state, llm_stage_detail
from crisis.pipeline.serialize import incident_response
from crisis.store import get_incident_store

ProgressCallback = Callable[[dict[str, Any]], None]

# Re-export for tests / scripts that imported helpers from runner
_failed_output = failed_specialist_output
_handoff = handoff_from_state
_llm_stage_detail = llm_stage_detail


def run_incident_pipeline(
    report: IncidentReport,
    on_progress: ProgressCallback | None = None,
) -> IncidentState:
    """Run the incident pipeline (LangGraph + Langfuse callbacks + SSE progress)."""
    return run_incident_via_langgraph(report, on_progress=on_progress)


def stream_incident_pipeline(report: IncidentReport) -> Iterator[str]:
    """SSE lines (data: {...}) for POST /incidents/stream."""
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
