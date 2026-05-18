from crisis.agents.recommendations import parse_recommendation_bullets

MESSY = """
## Summary
Overview text.

## Recommendations
### Immediate Actions:
- [1] Immediate Actions:
- [1] Shut affected valves when safe: Coordinate with traffic to shut off the water main.
- [1] The incident involves a combination of a flood and a water main break.

### Long-term Actions:
- [2] Long-term Actions:
- [2] Primary Liaison: City EOC Safety Desk
- [2] Evacuation routes: Establish and clearly communicate evacuation routes to Sector 7.
- [2] The proximity to City General Hospital necessitates special attention.

## Communication
Draft here.
"""


def test_parse_filters_headers_and_narrative():
    actions = parse_recommendation_bullets(MESSY)
    assert "[1] Immediate Actions:" not in actions
    assert not any(a.lower().startswith("the incident involves") for a in actions)
    assert not any(a.lower().startswith("the proximity") for a in actions)
    assert any("Shut affected valves" in a for a in actions)
    assert any("Evacuation routes" in a for a in actions)
    assert len(actions) <= 5
