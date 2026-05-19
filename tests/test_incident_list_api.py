import os

os.environ["DATABASE_URL"] = ""
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["CRISIS_USE_MOCK_LLM"] = "true"

from fastapi.testclient import TestClient

from crisis.api.main import app
from crisis.models.enums import Category, SeverityLevel
from crisis.models.schemas import Incident, IncidentReport, IncidentSummary
from crisis.store import get_incident_store

client = TestClient(app)


def _seed_incident(iid: str) -> None:
    report = IncidentReport(description="Test flood", location="Sector 1")
    inc = Incident(
        incident_id=iid,
        description=report.description,
        location=report.location,
        categories=[Category.FLOOD],
        severity=SeverityLevel.HIGH,
        confidence=0.9,
        original_report=report,
    )
    summary = IncidentSummary(
        incident_id=iid,
        categories=[Category.FLOOD],
        severity=SeverityLevel.HIGH,
        agent_outputs={},
        ranked_recommendations=[],
        communication_drafts=[],
    )
    get_incident_store().save_pipeline_result(
        {
            "incident": inc,
            "routing_decision": None,
            "specialist_outputs": {},
            "incident_summary": summary,
            "trace": [],
            "pipeline_stages": [],
        }
    )


def test_list_incidents_returns_summaries():
    _seed_incident("INC-LIST-A")
    r = client.get("/incidents", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    ids = [x["incident_id"] for x in body["incidents"]]
    assert "INC-LIST-A" in ids
