import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["DATABASE_URL"] = ""

from crisis.models.enums import SpecialistStatus
from crisis.models.schemas import IncidentReport
from crisis.pipeline.events import initial_stages, stage_index
from crisis.pipeline.graph_runner import _finalize_stages
from crisis.graph.incident_graph import run_incident_pipeline


def test_finalize_stages_marks_specialists_complete():
    from crisis.models.schemas import SpecialistOutput

    stages = initial_stages(["cyber"])
    stages[stage_index(stages, "run_specialists")].status = "running"  # type: ignore[attr-defined]
    state = {
        "specialist_outputs": {
            "cyber": SpecialistOutput(
                agent_id="cyber",
                workflow_id="cyber_containment",
                workflow_selection_rationale="",
                recommendations=[],
                communication_drafts=[],
                evidence=[],
                status=SpecialistStatus.COMPLETE,
                duration_ms=1200,
            )
        },
        "incident_summary": None,
    }
    out = _finalize_stages(state, stages)  # type: ignore[arg-type]
    cyber = next(s for s in out if s.id == "specialist:cyber")
    assert cyber.status == "complete"
    rs = next(s for s in out if s.id == "run_specialists")
    assert rs.status == "complete"


def test_pipeline_end_stages_all_complete():
    state = run_incident_pipeline(
        IncidentReport(
            description="Ransomware at hospital EMR systems.",
            location="City General Hospital",
        )
    )
    stages = state.get("pipeline_stages") or []
    assert stages
    assert all(s["status"] in ("complete", "error", "skipped") for s in stages)
    assert not any(s["status"] in ("pending", "running") for s in stages)
