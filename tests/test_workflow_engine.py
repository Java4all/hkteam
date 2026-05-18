import os

os.environ["CRISIS_USE_MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""

from crisis.agents.config_loader import load_agent_config, resolve_workflow, list_configured_agents
from crisis.agents.errors import AgentConfigError
from crisis.agents.workflow_overrides import parse_agent_workflow_overrides
from crisis.agents.workflow_select import select_workflow
from crisis.agents.specialist import run_specialist
from crisis.models.enums import SeverityLevel
from crisis.models.schemas import IncidentReport, RouterHandoff
from crisis.routing.classifier import classify_incident

EXPECTED_AGENTS = [
    "flood",
    "utilities",
    "infrastructure",
    "cyber",
    "comms",
    "public_safety",
    "public_services",
    "general",
]


def test_all_specialists_have_workflow_yaml():
    configured = list_configured_agents()
    for aid in EXPECTED_AGENTS:
        assert aid in configured, f"missing configs/agents/{aid}.yaml"
        cfg = load_agent_config(aid, reload=True)
        assert cfg and cfg.workflows


def test_load_flood_workflow_inherits():
    cfg = load_agent_config("flood", reload=True)
    assert cfg is not None
    wf = resolve_workflow(cfg, "flood_critical")
    ids = {a.id for a in wf.actions}
    assert "kb" in ids
    assert "analyze" in ids
    assert "evac" in ids


def test_flood_standard_has_parallel_context():
    cfg = load_agent_config("flood", reload=True)
    wf = resolve_workflow(cfg, "flood_standard")
    assert any(a.id == "context" and a.type == "parallel" for a in wf.actions)


def test_workflow_rules_critical_flood():
    cfg = load_agent_config("flood", reload=True)
    inc = classify_incident(
        IncidentReport(description="River flooding downtown.", location="Sector 7")
    )
    handoff = RouterHandoff(
        incident_id=inc.incident_id,
        categories=[c.value for c in inc.categories],
        severity=SeverityLevel.CRITICAL,
        location=inc.location,
        description=inc.description,
        confidence=inc.confidence,
        routing_hints=inc.routing_hints,
    )
    wf, reason = select_workflow("flood", handoff, config=cfg)
    assert wf == "flood_critical"
    assert "rule" in reason or "severity" in reason


def test_parse_workflow_overrides():
    assert parse_agent_workflow_overrides("flood:flood_light,utilities:utilities_standard") == {
        "flood": "flood_light",
        "utilities": "utilities_standard",
    }


def test_run_specialist_utilities():
    inc = classify_incident(
        IncidentReport(
            description="Water main burst flooding street.",
            location="Oak Street",
        )
    )
    handoff = RouterHandoff(
        incident_id=inc.incident_id,
        categories=[c.value for c in inc.categories],
        severity=inc.severity,
        location=inc.location,
        description=inc.description,
        confidence=inc.confidence,
        routing_hints=inc.routing_hints,
    )
    out = run_specialist("utilities", handoff)
    assert out.workflow_id
    assert out.recommendations


def test_missing_agent_config_raises():
    handoff = RouterHandoff(
        incident_id="x",
        categories=["OTHER"],
        severity=SeverityLevel.LOW,
        location="A",
        description="test",
        confidence=0.5,
    )
    try:
        run_specialist("nonexistent_agent", handoff)
        assert False, "expected AgentConfigError"
    except AgentConfigError:
        pass
