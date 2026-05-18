from __future__ import annotations

import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from crisis.dispatch.simulator import simulate_dispatch
from crisis.pipeline.serialize import incident_response
from crisis.pipeline.runner import run_incident_pipeline, stream_incident_pipeline
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
    modified_recommendations: dict[str, str] = Field(default_factory=dict)


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
    try:
        state = run_incident_pipeline(report)
    except Exception as exc:
        raise HTTPException(
            503,
            detail={
                "message": str(exc),
                "stage": "pipeline",
                "hint": "Check NVIDIA_API_KEY, API logs, or set CRISIS_USE_MOCK_LLM=true.",
            },
        ) from exc
    store.save_pipeline_result(state)
    return incident_response(state)


@app.post("/incidents/stream")
def create_incident_stream(report: IncidentReport):
    if not report.description.strip():
        raise HTTPException(400, detail={"missing_fields": ["description"]})
    if not report.location.strip():
        raise HTTPException(400, detail={"missing_fields": ["location"]})
    return StreamingResponse(
        stream_incident_pipeline(report),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
        "pipeline_stages": row.get("pipeline_stages", []),
    }


@app.post("/incidents/{incident_id}/decision")
def post_decision(incident_id: str, body: HumanDecisionRequest):
    row = get_incident_store().get(incident_id)
    if not row:
        raise HTTPException(404, detail="Incident not found")
    summary = row.get("incident_summary")
    known = (
        {r.id for r in summary.ranked_recommendations} if summary else set()
    )
    unknown = (
        set(body.approved_recommendation_ids)
        | {x for x in body.rejected_recommendation_ids if x != "*"}
        | set(body.modified_recommendations)
    ) - known
    if unknown and known:
        raise HTTPException(
            400,
            detail={"unknown_recommendation_ids": sorted(unknown)},
        )

    decision = HumanDecision(
        operator_id=body.operator_id,
        approved_recommendation_ids=body.approved_recommendation_ids,
        rejected_recommendation_ids=body.rejected_recommendation_ids,
        rejection_reason=body.rejection_reason,
        modified_recommendations=body.modified_recommendations,
    )
    if not get_incident_store().record_human_decision(incident_id, decision):
        raise HTTPException(404, detail="Incident not found")
    row = get_incident_store().get(incident_id)
    inc = row["incident"]
    summary = row.get("incident_summary")
    recs = summary.ranked_recommendations if summary else []
    dispatch_sim = simulate_dispatch(
        incident_id=incident_id,
        approved_ids=decision.approved_recommendation_ids,
        recommendations=recs,
        modified=decision.modified_recommendations,
        location=inc.location,
        simulation_mode=settings.simulation_mode,
    )
    dispatch_note = dispatch_sim["note"] if settings.simulation_mode else "Dispatch queued."
    return {
        "incident_id": incident_id,
        "status": inc.status.value,
        "decision": decision.model_dump(mode="json"),
        "dispatch": dispatch_note,
        "dispatch_simulation": dispatch_sim,
        "summary": {
            "approved_count": len(decision.approved_recommendation_ids),
            "rejected_count": len(
                [x for x in decision.rejected_recommendation_ids if x != "*"]
            ),
            "modified_count": len(decision.modified_recommendations),
        },
    }


def run():
    uvicorn.run(
        "crisis.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
