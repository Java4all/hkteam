"""Regression: review panel data must be built after incident response (no NameError)."""

import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["DATABASE_URL"] = ""

from crisis.ui.review_panel import recommendations_for_review


def test_recommendations_for_review_multi_agent_summary():
    summary = {
        "ranked_recommendations": [
            {
                "id": "rec-flood-1",
                "priority": 1,
                "action": "Monitor river gauges and pre-stage pumps in sectors 6–9.",
                "rationale": "flood",
                "evidence_ids": [],
            },
            {
                "id": "rec-utilities-1",
                "priority": 2,
                "action": "Coordinate with traffic for excavation of affected valves.",
                "rationale": "utilities",
                "evidence_ids": [],
            },
        ],
        "narrative": (
            "## Recommendations\n"
            "1. **Monitoring and Preparation:** Monitor river gauges.\n"
            "2. **Traffic Coordination:** Coordinate with traffic.\n"
        ),
    }
    recs = recommendations_for_review(summary, fallback_agent="flood")
    assert len(recs) >= 2
    assert all(r.get("action") for r in recs)
