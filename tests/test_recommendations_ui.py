from crisis.agents.recommendations import (
    parse_recommendation_bullets,
    recommendations_from_narrative,
    strip_recommendations_from_narrative,
)
from crisis.ui.review_panel import recommendations_for_review


def test_parse_numbered_recommendations_section():
    text = (
        "## Incident overview\n"
        "Hospital systems affected.\n\n"
        "## Recommendations\n"
        "1. Immediate containment and isolation of affected systems\n"
        "2. Activate incident response plan\n\n"
        "## Conflicts\n"
        "None.\n"
    )
    bullets = parse_recommendation_bullets(text, max_items=5)
    assert len(bullets) == 2
    assert "containment" in bullets[0].lower()


def test_strip_recommendations_from_narrative():
    text = (
        "## Summary\n"
        "Ransomware at hospital.\n\n"
        "## Recommendations\n"
        "- Isolate affected systems\n"
        "- Notify legal\n\n"
        "## Involved Specialists\n"
        "- Cyber\n"
    )
    stripped = strip_recommendations_from_narrative(text)
    assert "Recommendations" not in stripped
    assert "Involved Specialists" in stripped
    assert "Isolate" not in stripped


def test_recommendations_for_review_falls_back_to_narrative():
    summary = {
        "ranked_recommendations": [],
        "narrative": (
            "## Summary\n"
            "Clinical workflows degraded.\n\n"
            "## Recommendations\n"
            "- Immediate containment and isolation of affected systems\n"
            "- Collaboration with Cyber specialists\n"
        ),
    }
    recs = recommendations_for_review(summary, fallback_agent="cyber")
    assert len(recs) == 2
    assert recs[0]["id"].startswith("rec-cyber-")
    assert "containment" in recs[0]["action"].lower()


def test_recommendations_from_narrative_builds_dicts():
    recs = recommendations_from_narrative(
        "## Recommendations\n- Dispatch repair crew\n",
        agent_id="utilities",
    )
    assert recs[0]["id"] == "rec-utilities-1"
