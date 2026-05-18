from __future__ import annotations

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from contextlib import asynccontextmanager

from crisis.graph.incident_graph import run_incident_pipeline
from crisis.models.schemas import HumanDecision, IncidentReport
from crisis.llm.nvidia_health import nvidia_health
from crisis.observability.langfuse import langfuse_health
from crisis.settings import settings
from crisis.store import get_incident_store


@asynccontextmanager
async def lifespan(app):  # noqa: ARG001
    get_incident_store()
    yield


app = FastAPI(title="Smart City Crisis Management", version="1.0.0", lifespan=lifespan)


class HumanDecisionRequest(BaseModel):
    operator_id: str = "operator-1"
    approved_recommendation_ids: list[str] = Field(default_factory=list)
    rejected_recommendation_ids: list[str] = Field(default_factory=list)
    rejection_reason: str | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "llm_profile": settings.llm_profile,
        "mock_llm": settings.crisis_use_mock_llm,
        "simulation_mode": settings.simulation_mode,
        "database": bool(settings.database_url),
        "langfuse": langfuse_health(),
        "nvidia": nvidia_health(),
    }


@app.post("/incidents")
def create_incident(report: IncidentReport):
    if not report.description.strip():
        raise HTTPException(400, detail={"missing_fields": ["description"]})
    if not report.location.strip():
        raise HTTPException(400, detail={"missing_fields": ["location"]})
    store = get_incident_store()
    state = run_incident_pipeline(report)
    store.save_pipeline_result(state)
    inc = state["incident"]
    return {
        "incident_id": inc.incident_id,
        "status": inc.status.value,
        "categories": [c.value for c in inc.categories],
        "severity": inc.severity.value,
        "routing": state["routing_decision"].model_dump(),
        "summary": state["incident_summary"].model_dump(),
        "trace": state.get("trace", []),
    }


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    row = get_incident_store().get(incident_id)
    if not row:
        raise HTTPException(404, detail="Incident not found")
    inc = row["incident"]
    return {
        "incident_id": inc.incident_id,
        "status": inc.status.value,
        "incident": inc.model_dump(mode="json"),
        "routing_decision": row["routing_decision"].model_dump() if row.get("routing_decision") else None,
        "specialist_outputs": {
            k: v.model_dump() for k, v in (row.get("specialist_outputs") or {}).items()
        },
        "incident_summary": row["incident_summary"].model_dump() if row.get("incident_summary") else None,
        "human_decision": row["human_decision"].model_dump() if row.get("human_decision") else None,
        "trace": row.get("trace", []),
    }


@app.post("/incidents/{incident_id}/decision")
def post_decision(incident_id: str, body: HumanDecisionRequest):
    decision = HumanDecision(
        operator_id=body.operator_id,
        approved_recommendation_ids=body.approved_recommendation_ids,
        rejected_recommendation_ids=body.rejected_recommendation_ids,
        rejection_reason=body.rejection_reason,
    )
    if not get_incident_store().record_human_decision(incident_id, decision):
        raise HTTPException(404, detail="Incident not found")
    dispatch_note = "SIMULATION: no external dispatch." if settings.simulation_mode else "Dispatch queued."
    return {"incident_id": incident_id, "decision": decision.model_dump(mode="json"), "dispatch": dispatch_note}


def run():
    uvicorn.run(
        "crisis.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
