import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""

from crisis.api.main import _recommendations_for_dispatch
from crisis.dispatch.simulator import simulate_dispatch
from crisis.models.enums import Category, SeverityLevel
from crisis.models.schemas import IncidentSummary, Recommendation
from crisis.ui.dispatch_display import (
    format_dispatch_in_progress,
    format_dispatch_simulation,
    format_dispatch_summary_table,
)
from crisis.ui.incident_history import format_incident_sidebar_html


def test_simulate_dispatch_builds_entries_for_approved():
    recs = [
        Recommendation(
            id="rec-flood-1",
            priority=1,
            action="Deploy sandbags to riverside blocks.",
            rationale="test",
        ),
        Recommendation(
            id="rec-utilities-2",
            priority=2,
            action="Isolate water main segment 7B.",
            rationale="test",
        ),
    ]
    out = simulate_dispatch(
        incident_id="inc-001",
        approved_ids=["rec-flood-1"],
        recommendations=recs,
        location="Sector 7",
        simulation_mode=True,
    )
    assert out["simulated"] is True
    assert out["dispatched_count"] == 1
    assert out["entries"][0]["reference"].startswith("SIM-")
    assert out["entries"][0]["target_system"] == "Flood Control CAD"
    assert "sandbags" in out["entries"][0]["action"]


def test_simulate_dispatch_empty_when_none_approved():
    out = simulate_dispatch(
        incident_id="inc-001",
        approved_ids=[],
        recommendations=[],
        simulation_mode=True,
    )
    assert out["dispatched_count"] == 0
    assert out["entries"] == []


def test_recommendations_for_dispatch_merges_review_snapshot():
    summary = IncidentSummary(
        incident_id="INC-TEST",
        categories=[Category.UTILITIES],
        severity=SeverityLevel.HIGH,
        agent_outputs={},
        ranked_recommendations=[],
        communication_drafts=[],
        narrative="## Recommendations\n- Shut valve\n",
    )
    review = [
        {
            "id": "rec-utilities-1",
            "priority": 1,
            "action": "Shut valve on Oak Street main.",
            "rationale": "",
        }
    ]
    merged = _recommendations_for_dispatch(summary, review)
    assert len(merged) == 1
    assert merged[0].id == "rec-utilities-1"
    out = simulate_dispatch(
        incident_id="INC-TEST",
        approved_ids=["rec-utilities-1"],
        recommendations=merged,
        simulation_mode=True,
    )
    assert out["dispatched_count"] == 1
    assert "Shut valve" in out["entries"][0]["action"]


def test_format_dispatch_in_progress_shows_spinner():
    html = format_dispatch_in_progress(
        frame=1, phase="Dispatching", detail="SIM-ABC → CAD", completed=1, total=3
    )
    assert "in progress" in html
    assert "Dispatching" in html
    assert "SIM-ABC" in html


def test_format_dispatch_summary_table():
    html = format_dispatch_summary_table(
        {
            "dispatched_count": 1,
            "location": "Oak St",
            "entries": [
                {
                    "reference": "SIM-X",
                    "specialist": "Utilities",
                    "target_system": "OMS",
                    "channel": "API",
                    "status": "ACKNOWLEDGED (simulated)",
                }
            ],
        },
        decision_summary={"approved_count": 1, "rejected_count": 0},
    )
    assert "| Approved | 1 |" in html
    assert "SIM-X" in html


def test_format_incident_sidebar_has_tabs():
    html = format_incident_sidebar_html(
        current_id="INC-1",
        current_summary={
            "incident_id": "INC-1",
            "status": "AWAITING_HUMAN",
            "severity": "HIGH",
            "categories": ["UTILITIES"],
            "location": "Oak",
            "recommendation_count": 3,
            "approved_count": 0,
            "rejected_count": 0,
        },
        history=[
            {
                "incident_id": "INC-1",
                "status": "AWAITING_HUMAN",
                "severity": "HIGH",
                "location": "Oak",
            }
        ],
    )
    assert 'data-crisis-tab="current"' in html
    assert 'data-crisis-tab="history"' in html
    assert "INC-1" in html


def test_format_dispatch_simulation_renders_entries():
    html = format_dispatch_simulation(
        {
            "simulated": True,
            "location": "Oak Street",
            "entries": [
                {
                    "reference": "SIM-ABC123",
                    "specialist": "Flood",
                    "target_system": "Flood Control CAD",
                    "channel": "CAD API",
                    "status": "ACKNOWLEDGED (simulated)",
                    "action": "Deploy sandbags.",
                }
            ],
            "note": "No external systems contacted.",
        }
    )
    assert "Dispatch simulation complete" in html
    assert "SIM-ABC123" in html
    assert "Flood Control CAD" in html
    assert "Summary" in html
