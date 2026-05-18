from __future__ import annotations

from threading import Lock
from typing import Any

from crisis.models.schemas import HumanDecision
from crisis.store.human_decision import apply_human_decision


class MemoryIncidentStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._incidents: dict[str, dict[str, Any]] = {}

    def save_pipeline_result(self, state: dict[str, Any]) -> None:
        incident: Incident = state["incident"]
        with self._lock:
            self._incidents[incident.incident_id] = {
                "incident": incident,
                "routing_decision": state.get("routing_decision"),
                "specialist_outputs": state.get("specialist_outputs"),
                "incident_summary": state.get("incident_summary"),
                "trace": state.get("trace", []),
                "pipeline_stages": state.get("pipeline_stages", []),
                "human_decision": state.get("human_decision"),
            }

    def get(self, incident_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._incidents.get(incident_id)

    def record_human_decision(self, incident_id: str, decision: HumanDecision) -> bool:
        with self._lock:
            row = self._incidents.get(incident_id)
            if not row:
                return False
            apply_human_decision(row, decision)
            return True

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._incidents.keys())


incident_store = MemoryIncidentStore()
