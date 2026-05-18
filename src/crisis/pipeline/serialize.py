from __future__ import annotations

from typing import Any

from crisis.graph.state import IncidentState


def incident_response(state: IncidentState) -> dict[str, Any]:
    inc = state["incident"]
    summary = state.get("incident_summary")
    routing = state.get("routing_decision")
    return {
        "incident_id": inc.incident_id,
        "status": inc.status.value,
        "categories": [c.value for c in inc.categories],
        "severity": inc.severity.value,
        "routing": routing.model_dump() if routing else None,
        "summary": summary.model_dump() if summary else None,
        "trace": state.get("trace", []),
        "pipeline_stages": state.get("pipeline_stages", []),
    }
