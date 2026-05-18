from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from langgraph.graph import END, START, StateGraph

from crisis.agents.aggregator import aggregate_outputs
from crisis.agents.specialist import run_specialist
from crisis.graph.state import IncidentState
from crisis.models.enums import IncidentStatus
from crisis.models.schemas import IncidentReport, RouterHandoff
from crisis.routing.classifier import classify_incident
from crisis.routing.smart_router import route_incident


def _trace(state: IncidentState, msg: str) -> list[str]:
    t = list(state.get("trace") or [])
    t.append(msg)
    return t


def node_intake(state: IncidentState) -> IncidentState:
    report = state["report"]
    incident = classify_incident(report)
    incident.status = IncidentStatus.CLASSIFIED
    return {
        "incident": incident,
        "trace": _trace(state, f"classified:{','.join(c.value for c in incident.categories)}"),
    }


def node_smart_route(state: IncidentState) -> IncidentState:
    incident = state["incident"]
    decision = route_incident(incident)
    incident.status = IncidentStatus.ANALYZING
    return {
        "incident": incident,
        "routing_decision": decision,
        "trace": _trace(state, f"routed:{','.join(decision.selected)} mode={decision.selection_mode}"),
    }


def _handoff(incident, routing) -> RouterHandoff:
    return RouterHandoff(
        incident_id=incident.incident_id,
        categories=[c.value for c in incident.categories],
        severity=incident.severity,
        location=incident.location,
        description=incident.description,
        confidence=incident.confidence,
        routing_hints=incident.routing_hints,
        activated_reason=routing.rationale,
    )


def node_run_specialists(state: IncidentState) -> IncidentState:
    incident = state["incident"]
    routing = state["routing_decision"]
    handoff = _handoff(incident, routing)
    outputs: dict[str, SpecialistOutput] = {}

    def _run(agent_id: str) -> tuple[str, SpecialistOutput]:
        return agent_id, run_specialist(agent_id, handoff)

    if routing.execution_mode == "parallel" and len(routing.selected) > 1:
        with ThreadPoolExecutor(max_workers=len(routing.selected)) as pool:
            futs = {pool.submit(_run, a): a for a in routing.selected}
            for fut in as_completed(futs):
                aid, out = fut.result()
                outputs[aid] = out
    else:
        for aid in routing.selected:
            _, out = _run(aid)
            outputs[aid] = out

    return {
        "specialist_outputs": outputs,
        "trace": _trace(state, f"specialists_done:{','.join(outputs.keys())}"),
    }


def node_aggregate(state: IncidentState) -> IncidentState:
    incident = state["incident"]
    outputs = state.get("specialist_outputs") or {}
    summary = aggregate_outputs(incident, outputs)
    incident.status = IncidentStatus.AWAITING_HUMAN
    return {
        "incident_summary": summary,
        "incident": incident,
        "trace": _trace(state, "aggregated"),
    }


def build_incident_graph():
    g = StateGraph(IncidentState)
    g.add_node("intake", node_intake)
    g.add_node("smart_route", node_smart_route)
    g.add_node("run_specialists", node_run_specialists)
    g.add_node("aggregate", node_aggregate)
    g.add_edge(START, "intake")
    g.add_edge("intake", "smart_route")
    g.add_edge("smart_route", "run_specialists")
    g.add_edge("run_specialists", "aggregate")
    g.add_edge("aggregate", END)
    return g.compile()


def run_incident_pipeline(report: IncidentReport) -> IncidentState:
    graph = build_incident_graph()
    init: IncidentState = {
        "report": report,
        "trace": ["start"],
    }
    return graph.invoke(init)
