import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""

from crisis.dispatch.simulator import simulate_dispatch
from crisis.models.schemas import Recommendation
from crisis.ui.dispatch_display import format_dispatch_simulation


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
    assert "Dispatch simulation" in html
    assert "SIM-ABC123" in html
    assert "Flood Control CAD" in html
