"""Demo tests — mock LLM, no NVIDIA cloud or local NIM required."""

import os

import pytest

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["LLM_PROFILE"] = "multimodel"
os.environ["DATABASE_URL"] = ""
os.environ["LANGFUSE_ENABLED"] = "false"

from crisis.graph.incident_graph import run_incident_pipeline
from crisis.models.enums import Category, SeverityLevel
from crisis.models.schemas import IncidentReport
from crisis.routing.classifier import classify_incident
from crisis.routing.smart_router import route_incident


def test_classify_utilities():
    inc = classify_incident(
        IncidentReport(
            description="Water main pipe burst with flooding on the road.",
            location="Oak Street",
        )
    )
    assert Category.UTILITIES in inc.categories


def test_smart_route_multi_category():
    inc = classify_incident(
        IncidentReport(
            description="River flooding and broken water pipe near hospital.",
            location="Sector 7",
        )
    )
    decision = route_incident(inc)
    assert len(decision.selected) >= 1
    assert decision.incident_id == inc.incident_id


def test_pipeline_utilities_scenario():
    state = run_incident_pipeline(
        IncidentReport(
            description="Major water main rupture on Oak Street.",
            location="Oak Street, Sector 7",
        )
    )
    assert state["incident"].incident_id.startswith("INC-")
    assert state["routing_decision"].selected
    assert state["specialist_outputs"]
    assert state["incident_summary"].ranked_recommendations
    assert state["incident"].status.value == "AWAITING_HUMAN"


def test_pipeline_critical_multi_agent():
    state = run_incident_pipeline(
        IncidentReport(
            description="City-wide flood CRITICAL. Multiple districts. Hospital at risk.",
            location="Metro riverside",
        )
    )
    assert state["incident"].severity == SeverityLevel.CRITICAL
    assert len(state["routing_decision"].selected) >= 2


def test_per_agent_llm_metadata():
    state = run_incident_pipeline(
        IncidentReport(description="Cyber ransomware at city data center.", location="DC-West")
    )
    for _aid, out in state["specialist_outputs"].items():
        assert out.llm_model
        assert out.workflow_id
