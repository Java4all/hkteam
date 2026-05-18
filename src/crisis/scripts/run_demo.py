"""Run scripted demo scenarios (NVIDIA cloud LLM by default; mock if no API key)."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("LLM_PROFILE", "multimodel")
os.environ.setdefault("SIMULATION_MODE", "true")

_key = os.environ.get("NVIDIA_API_KEY", "")
if os.environ.get("CRISIS_USE_MOCK_LLM", "").lower() == "true" or not _key or _key == "x":
    os.environ["CRISIS_USE_MOCK_LLM"] = "true"
    print("(No NVIDIA_API_KEY — using mock LLM. Set NVIDIA_API_KEY in .env for cloud.)\n")
else:
    os.environ.setdefault("CRISIS_USE_MOCK_LLM", "false")
    print("(Using NVIDIA cloud LLM — multimodel profile.)\n")

from crisis.agents.display import agent_display_name
from crisis.graph.incident_graph import run_incident_pipeline
from crisis.models.schemas import IncidentReport


SCENARIOS = [
    {
        "name": "utilities_water_main",
        "description": "Major water main rupture. Water flooding Oak Street.",
        "location": "Oak Street, Sector 7",
    },
    {
        "name": "flood_and_utilities",
        "description": "River overflow and water pipe burst near City General Hospital. Roads flooded.",
        "location": "Sector 7, riverside",
    },
    {
        "name": "cyber_hospital",
        "description": "Ransomware attack on hospital EMR systems. Clinical workflows degraded.",
        "location": "City General Hospital IT center",
    },
]


def main() -> int:
    mode = "mock LLM" if os.environ.get("CRISIS_USE_MOCK_LLM") == "true" else "NVIDIA cloud LLM"
    print(f"Smart City Crisis Management — demo run ({mode})\n")
    for sc in SCENARIOS:
        print("=" * 60)
        print(f"Scenario: {sc['name']}")
        report = IncidentReport(description=sc["description"], location=sc["location"])
        state = run_incident_pipeline(report)
        inc = state["incident"]
        routing = state["routing_decision"]
        print(f"  Incident ID: {inc.incident_id}")
        print(f"  Categories: {[c.value for c in inc.categories]}")
        print(f"  Severity: {inc.severity.value}")
        print(f"  Specialists: {routing.selected} ({routing.selection_mode})")
        for aid in (state.get("specialist_outputs") or {}):
            print(f"    - {agent_display_name(aid)}")
        summary = state["incident_summary"]
        print(f"  Recommendations: {len(summary.ranked_recommendations)}")
        print(f"  Trace: {' -> '.join(state.get('trace', []))}")
        print()
    print("Demo complete. Start API: crisis-api | UI: chainlit run src/crisis/ui/chainlit_app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
