from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from crisis.models.enums import IncidentStatus
from crisis.models.schemas import (
    HumanDecision,
    Incident,
    IncidentSummary,
    RoutingDecision,
    SpecialistOutput,
)


class PostgresIncidentStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._ensure_schema()

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents (created_at DESC);
                """
            )
            conn.commit()

    @staticmethod
    def _serialize_state(state: dict[str, Any]) -> dict[str, Any]:
        routing = state.get("routing_decision")
        summary = state.get("incident_summary")
        outputs = state.get("specialist_outputs") or {}
        human = state.get("human_decision")
        return {
            "incident": state["incident"].model_dump(mode="json"),
            "routing_decision": routing.model_dump(mode="json") if routing else None,
            "specialist_outputs": {k: v.model_dump(mode="json") for k, v in outputs.items()},
            "incident_summary": summary.model_dump(mode="json") if summary else None,
            "human_decision": human.model_dump(mode="json") if human else None,
            "trace": state.get("trace", []),
            "pipeline_stages": state.get("pipeline_stages", []),
        }

    @staticmethod
    def _deserialize_row(payload: dict[str, Any]) -> dict[str, Any]:
        incident = Incident.model_validate(payload["incident"])
        routing = (
            RoutingDecision.model_validate(payload["routing_decision"])
            if payload.get("routing_decision")
            else None
        )
        outputs = {
            k: SpecialistOutput.model_validate(v)
            for k, v in (payload.get("specialist_outputs") or {}).items()
        }
        summary = (
            IncidentSummary.model_validate(payload["incident_summary"])
            if payload.get("incident_summary")
            else None
        )
        human = (
            HumanDecision.model_validate(payload["human_decision"])
            if payload.get("human_decision")
            else None
        )
        return {
            "incident": incident,
            "routing_decision": routing,
            "specialist_outputs": outputs,
            "incident_summary": summary,
            "human_decision": human,
            "trace": payload.get("trace", []),
            "pipeline_stages": payload.get("pipeline_stages", []),
        }

    def save_pipeline_result(self, state: dict[str, Any]) -> None:
        incident: Incident = state["incident"]
        payload = self._serialize_state(state)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO incidents (incident_id, payload)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (incident_id) DO UPDATE
                SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (incident.incident_id, json.dumps(payload)),
            )
            conn.commit()

    def get(self, incident_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM incidents WHERE incident_id = %s",
                (incident_id,),
            ).fetchone()
        if not row:
            return None
        return self._deserialize_row(row["payload"])

    def record_human_decision(self, incident_id: str, decision: HumanDecision) -> bool:
        row = self.get(incident_id)
        if not row:
            return False
        row["human_decision"] = decision
        inc: Incident = row["incident"]
        if decision.rejected_recommendation_ids and not decision.approved_recommendation_ids:
            inc.status = IncidentStatus.REJECTED
        else:
            inc.status = IncidentStatus.APPROVED
        payload = self._serialize_state(row)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE incidents SET payload = %s::jsonb, updated_at = NOW()
                WHERE incident_id = %s
                """,
                (json.dumps(payload), incident_id),
            )
            conn.commit()
        return True

    def list_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT incident_id FROM incidents ORDER BY created_at DESC"
            ).fetchall()
        return [r["incident_id"] for r in rows]
