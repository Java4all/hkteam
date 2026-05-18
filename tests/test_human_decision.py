import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""

from crisis.models.schemas import HumanDecision, IncidentReport, Recommendation
from crisis.graph.incident_graph import run_incident_pipeline
from crisis.store.memory import MemoryIncidentStore
from crisis.store.human_decision import apply_human_decision
from crisis.ui.review_panel import unique_recommendations_for_review


def test_partial_approve_with_edit():
    state = run_incident_pipeline(
        IncidentReport(description="Water main burst on Oak Street.", location="Oak Street")
    )
    store = MemoryIncidentStore()
    store.save_pipeline_result(state)
    iid = state["incident"].incident_id
    recs = state["incident_summary"].ranked_recommendations
    assert len(recs) >= 1
    rid = recs[0].id

    decision = HumanDecision(
        operator_id="test-op",
        approved_recommendation_ids=[rid],
        rejected_recommendation_ids=[recs[1].id] if len(recs) > 1 else [],
        modified_recommendations={rid: "Dispatch crew A to Oak Street within 30 minutes."},
    )
    row = store.get(iid)
    apply_human_decision(row, decision)
    updated = row["incident_summary"].ranked_recommendations[0]
    assert "Dispatch crew A" in updated.action
    assert row["incident"].status.value == "APPROVED"


def test_unique_recommendations_for_review_dedupes():
    recs = [
        {"id": "a", "action": "Same action"},
        {"id": "b", "action": "Same action"},
        {"id": "c", "action": "Different"},
    ]
    out = unique_recommendations_for_review(recs)
    assert len(out) == 2
