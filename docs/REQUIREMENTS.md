# Requirements Document — Smart City Crisis Management

| Field | Value |
|-------|--------|
| **Product** | Smart City Crisis Management System |
| **Version** | 1.0 (application) |
| **Architecture** | [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) · [AGENTS.md](AGENTS.md) |

## v1.0 implementation notes

This document is the **product requirements baseline**. The shipped v1.0 app maps to it as follows:

| Requirement area | v1.0 implementation |
|------------------|----------------------|
| Observability | **Langfuse v3** (compose stack) |
| Deployment | **Docker Compose** on NVIDIA GPU instance |
| LLM | **NVIDIA cloud** (`integrate.api.nvidia.com`), per-agent models in `configs/llm/multimodel.yaml` |
| Specialist execution | **YAML workflow per agent** (`configs/agents/{id}.yaml`) — tools, LLM, parallel, subagent |
| Agent config reload | **Container restart** required (no hot-reload in v1.0) |
| Operator UI | **Chainlit** — per-recommendation approve/reject, Submit for dispatch simulation |
| Dispatch | **Simulation only** (`SIMULATION_MODE`); no live external adapters |
| Comms specialist | Activated by Smart Router for HIGH/CRITICAL; may run as **subagent** inside flood workflows |
| Knowledge / tools | File-based playbook RAG; weather/GIS stubs |

Deferred or partial vs acceptance criteria: live SCADA/CAD, NAT `nat_workflow` execution, 90-day audit retention UI, mid-workflow switch, full escalation re-router.

---

## Introduction

The Smart City Crisis Management System is a multi-agent AI application designed to assist city special response teams in coordinating and managing urban crisis situations in real time. The system accepts incident reports, categorizes and filters them, routes them to specialized AI agents, and presents actionable recommendations to a human decision maker. Supported scenarios include floods, infrastructure failures, cyberattacks, public sector service disruptions, public safety incidents, utility failures (e.g., broken water pipes), and other urban emergencies.

The system is built on **NVIDIA cloud LLMs**, orchestrated via **LangGraph**, with **Langfuse** for observability. Each specialist agent runs a **configurable workflow** and may use a **different LLM model** (assigned in `configs/llm/multimodel.yaml`). Human-in-the-loop is a core design principle: the system proposes recommendations but final decisions always rest with the human operator.

---

## Glossary

- **System**: The Smart City Crisis Management System as a whole.
- **Incident**: A reported urban emergency or crisis event submitted to the System.
- **Incident_Report**: A structured or unstructured input describing an Incident, including type, location, severity, and available details.
- **Intake_Agent**: The component responsible for receiving, validating, and normalizing Incident_Reports (API intake node).
- **Classifier_Agent**: The component responsible for filtering, categorizing, and assigning severity to an Incident.
- **Smart_Router**: The orchestration layer that selects which Specialist_Agents to run (subset of candidates).
- **Router**: See Smart_Router (requirements term; implemented as Smart Router + fan-out).
- **Specialist_Agent**: A domain-specific agent (e.g., Flood, Cyber, Infrastructure, Utilities, Public_Safety, Public_Services, Comms, General) responsible for analysis and recommendations.
- **Agent_Workflow**: A named sequence of actions (tools, LLM, parallel branches, subagents) defined in `configs/agents/{id}.yaml`.
- **Aggregator_Agent**: The component that consolidates Specialist_Agent outputs into a unified summary.
- **Human_Operator**: The authorized city official who reviews output and makes final decisions.
- **Recommendation**: A proposed action for Human_Operator review.
- **Communication_Draft**: A pre-composed message or alert for dispatch after approval.
- **Severity_Level**: LOW, MEDIUM, HIGH, or CRITICAL.
- **Agent_Config**: Per-agent LLM and workflow configuration (YAML + multimodel assignments).
- **Orchestrator**: The LangGraph-based pipeline (intake → classify → route → specialists → aggregate → HITL).
- **Observability_Platform**: **Langfuse** — traces, spans, and LLM call logging.
- **Knowledge_Base**: City-specific data, playbooks, and catalogs under `data/`.
- **Escalation**: Elevating an Incident to additional Specialist_Agents or human attention.
- **Subagent**: A child Specialist_Agent invoked inside a parent Agent_Workflow.

---

## Requirements

### Requirement 1: Incident Ingestion

**User Story:** As a Human_Operator, I want to submit an Incident_Report through the System, so that the crisis management workflow is initiated promptly.

#### Acceptance Criteria

1. THE Intake_Agent SHALL accept Incident_Reports submitted via a structured API endpoint or a natural-language input interface.
2. WHEN an Incident_Report is received, THE Intake_Agent SHALL validate that the report contains at minimum a non-empty incident description and a non-empty location field.
3. IF an Incident_Report is missing one or more required fields, THEN THE Intake_Agent SHALL return a validation error response that lists each absent field by name.
4. WHEN a valid Incident_Report is received, THE Intake_Agent SHALL normalize the report into a canonical Incident object and pass it to the Classifier_Agent within 5 seconds.
5. THE Intake_Agent SHALL assign a system-generated, non-reusable unique incident identifier to each Incident upon creation.
6. THE System SHALL preserve the original Incident_Report alongside the normalized Incident object for audit purposes.
7. IF the Classifier_Agent is unavailable when the Intake_Agent attempts to pass a normalized Incident, THEN THE Intake_Agent SHALL retain the Incident in a pending queue and retry delivery at 10-second intervals until the Classifier_Agent becomes available or a system administrator intervenes.

---

### Requirement 2: Incident Classification and Filtering

**User Story:** As a Human_Operator, I want each incident to be automatically categorized and assigned a severity level, so that the right specialist resources are engaged without delay.

#### Acceptance Criteria

1. WHEN a normalized Incident is received, THE Classifier_Agent SHALL assign it to one or more of the following categories: FLOOD, INFRASTRUCTURE, CYBER, PUBLIC_SAFETY, PUBLIC_SERVICES, UTILITIES, or OTHER.
2. WHEN a normalized Incident is received, THE Classifier_Agent SHALL assign a Severity_Level according to the following rules: CRITICAL if the incident description indicates immediate threat to life or critical infrastructure; HIGH if it indicates significant service disruption or property damage; MEDIUM if it indicates localized disruption with no immediate life threat; LOW if it indicates a minor or contained issue.
3. THE Classifier_Agent SHALL produce a classification confidence score between 0.0 and 1.0 for each assigned category.
4. IF the Classifier_Agent assigns a confidence score below 0.6 for one or more categories but at least one category has a score of 0.6 or above, THEN THE Classifier_Agent SHALL retain only the categories with a confidence score of 0.6 or above and proceed with routing.
5. IF the Classifier_Agent assigns a confidence score below 0.6 for all categories, THEN THE Classifier_Agent SHALL assign the category OTHER, set the Incident status to PENDING_REVIEW, and withhold the Incident from routing until the Human_Operator reviews and confirms or overrides the classification.
6. WHEN classification is complete, THE Classifier_Agent SHALL pass the classified Incident to the Router within 10 seconds.
7. THE Classifier_Agent SHALL log all classification decisions and confidence scores to the Observability_Platform.
8. IF the Classifier_Agent receives a malformed or incomplete Incident object, THEN THE Classifier_Agent SHALL reject the Incident with an error response identifying the missing or invalid fields and SHALL NOT route the Incident.

---

### Requirement 3: Incident Routing

**User Story:** As a Human_Operator, I want incidents to be automatically routed to the appropriate specialist agents, so that domain-specific analysis begins immediately.

#### Acceptance Criteria

1. WHEN a classified Incident is received, THE Router SHALL activate one or more Specialist_Agents whose registered categories match the Incident's assigned categories.
2. WHEN an Incident has a Severity_Level of CRITICAL, THE Router SHALL activate all Specialist_Agents whose registered categories match the Incident's assigned categories simultaneously, without waiting for any individual agent to complete.
3. WHEN an Incident has a Severity_Level of LOW or MEDIUM, THE Router SHALL activate Specialist_Agents sequentially in ascending order of their assigned category priority rank, where lower rank numbers are activated first.
4. THE Router SHALL pass the full classified Incident object, including category, Severity_Level, and confidence scores, to each activated Specialist_Agent.
5. IF no Specialist_Agent exists for an assigned category, THEN THE Router SHALL route the Incident to the designated fallback Specialist_Agent and notify the Human_Operator with a message indicating the unmatched category.
6. IF the designated fallback Specialist_Agent is also unavailable, THEN THE Router SHALL escalate the Incident directly to the Human_Operator with a message indicating that no capable agent is available for the unmatched category.
7. IF one or more Specialist_Agents fail to activate within 30 seconds of being triggered, THEN THE Router SHALL notify the Human_Operator with a message indicating which agents failed to activate and SHALL continue activating the remaining agents.
8. THE Router SHALL record each routing decision in the Observability_Platform, including the Incident identifier, the Severity_Level, the list of activated Specialist_Agents, the activation mode (parallel or sequential), and the timestamp of each activation.

*v1.0 note:* Smart Router may cap parallel specialists (e.g. max 4) and add Comms for HIGH/CRITICAL — see `configs/smart_routing/`.

---

### Requirement 4: Specialist Agent Analysis — Flood

**User Story:** As a Human_Operator, I want the Flood_Agent to analyze flood incidents and propose coordinated response actions, so that I can make informed decisions quickly.

#### Acceptance Criteria

1. WHEN a FLOOD-categorized Incident is received, THE Flood_Agent SHALL retrieve relevant weather data, flood zone maps, and historical flood records from the Knowledge_Base.
2. IF the Knowledge_Base is unavailable or returns incomplete data when the Flood_Agent attempts retrieval, THEN THE Flood_Agent SHALL proceed with the data successfully retrieved, note each unavailable data source by name in its output, and continue analysis.
3. WHEN a FLOOD-categorized Incident is received, THE Flood_Agent SHALL assess the affected area, estimated population at risk, and available evacuation routes.
4. WHEN the Flood_Agent has completed its assessment, THE Flood_Agent SHALL generate a prioritized list of Recommendations, ordered from highest to lowest urgency, including at minimum one evacuation-related action, one emergency service deployment action, and one infrastructure protection measure.
5. WHEN the Flood_Agent has completed its assessment, THE Flood_Agent SHALL produce a Communication_Draft addressed to the authorities identified as relevant in the Knowledge_Base for the affected area (e.g., emergency services, utility operators, transport authority).
6. IF the flood Severity_Level is CRITICAL, THEN THE Flood_Agent SHALL include a Recommendation to escalate to national emergency services; IF the escalation mechanism is unavailable, THEN THE Flood_Agent SHALL log the failure with the reason and continue without escalation.
7. THE Flood_Agent SHALL complete its analysis and produce both the Recommendations list and the Communication_Draft within 60 seconds of receiving the Incident.

*v1.0 note:* Implemented via `configs/agents/flood.yaml` workflows (e.g. `flood_standard`, `flood_critical`, `flood_dam_breach` with optional comms subagent).

---

### Requirement 5: Specialist Agent Analysis — Infrastructure

**User Story:** As a Human_Operator, I want the Infrastructure_Agent to analyze city infrastructure failures and propose repair and safety actions, so that disruption is minimized.

#### Acceptance Criteria

1. WHEN an INFRASTRUCTURE-categorized Incident is received, THE Infrastructure_Agent SHALL retrieve infrastructure asset records, maintenance history, and dependency maps from the Knowledge_Base.
2. WHEN the Infrastructure_Agent has completed retrieval, THE Infrastructure_Agent SHALL identify cascading failure risks as an observable list of dependent assets that may be affected if the reported asset fails, based on the dependency maps.
3. WHEN the Infrastructure_Agent has completed its assessment, THE Infrastructure_Agent SHALL generate Recommendations for immediate safety measures, repair prioritization, and public communication.
4. WHEN the Severity_Level is HIGH or CRITICAL, or when the affected asset is tagged as serving critical services in the Knowledge_Base, THE Infrastructure_Agent SHALL produce a Communication_Draft for the relevant city maintenance department and for public notification channels.
5. IF the infrastructure failure affects an asset tagged in the Knowledge_Base as serving critical services (e.g., hospitals, emergency services), meaning the asset's failure results in full or partial loss of that service, THEN THE Infrastructure_Agent SHALL escalate the Incident Severity_Level to CRITICAL and notify the Human_Operator.
6. THE Infrastructure_Agent SHALL complete its analysis, producing both the Recommendations list and the Communication_Draft (where applicable), within 60 seconds of receiving the Incident.

---

### Requirement 6: Specialist Agent Analysis — Cyber

**User Story:** As a Human_Operator, I want the Cyber_Agent to analyze cyberattack incidents and propose containment and recovery actions, so that city digital systems are protected.

#### Acceptance Criteria

1. WHEN a CYBER-categorized Incident is received, THE Cyber_Agent SHALL retrieve the inventory of affected systems, known threat signatures, and incident response playbooks from the Knowledge_Base; IF any Knowledge_Base component is unavailable, THEN THE Cyber_Agent SHALL proceed with the successfully retrieved components and note each unavailable component by name in its output.
2. WHEN the Cyber_Agent has completed retrieval, THE Cyber_Agent SHALL assess the scope of the attack, the list of affected services, and the potential data exposure.
3. WHEN the Cyber_Agent has completed its assessment, THE Cyber_Agent SHALL generate Recommendations for containment, system isolation, and recovery steps.
4. WHEN the Cyber_Agent has completed its assessment, THE Cyber_Agent SHALL produce a Communication_Draft for the city IT security team; IF the affected systems include assets tagged in the Knowledge_Base as law-enforcement-reportable or nationally-reportable, THEN the Communication_Draft SHALL also address the relevant law enforcement and national cybersecurity authorities.
5. IF the cyberattack affects systems tagged in the Knowledge_Base as critical infrastructure, THEN THE Cyber_Agent SHALL include a Recommendation to activate the city's cyber incident response plan.
6. THE Cyber_Agent SHALL complete its analysis, producing both the Recommendations list and the Communication_Draft, within 60 seconds of receiving the Incident.

---

### Requirement 7: Specialist Agent Analysis — Public Safety (Terrorist Attack / Civil Unrest)

**User Story:** As a Human_Operator, I want the PublicSafety_Agent to analyze public safety threats and propose law enforcement and public protection actions, so that civilian safety is prioritized.

#### Acceptance Criteria

1. WHEN a PUBLIC_SAFETY-categorized Incident is received, THE PublicSafety_Agent SHALL retrieve threat intelligence, affected area profiles, and emergency response protocols from the Knowledge_Base.
2. WHEN a PUBLIC_SAFETY-categorized Incident is received, THE PublicSafety_Agent SHALL assess the threat type, the affected zones expressed as named geographic areas or perimeter radii, and the estimated civilian exposure expressed as a numeric population range.
3. WHEN the PublicSafety_Agent has completed its assessment, THE PublicSafety_Agent SHALL generate Recommendations for law enforcement deployment, area cordoning, and public communication.
4. WHEN the PublicSafety_Agent has completed its assessment, THE PublicSafety_Agent SHALL produce a Communication_Draft addressed to at minimum police, fire services, and emergency medical services, including the threat type, affected zones, and recommended immediate actions.
5. IF the Severity_Level is CRITICAL, THEN THE PublicSafety_Agent SHALL include a Recommendation to notify national security and counter-terrorism authorities.
6. THE PublicSafety_Agent SHALL complete its analysis and produce both the Recommendations list and the Communication_Draft within 45 seconds of receiving the Incident.
7. IF the PublicSafety_Agent has not produced complete output within 45 seconds, THEN THE PublicSafety_Agent SHALL emit a partial output containing all analysis completed to that point, with an indication that the output is incomplete, and continue processing.
8. IF the Knowledge_Base is unavailable when the PublicSafety_Agent attempts retrieval, THEN THE PublicSafety_Agent SHALL proceed using only the Incident data provided, flag the Knowledge_Base unavailability in its output, and continue analysis.

---

### Requirement 8: Specialist Agent Analysis — Utilities

**User Story:** As a Human_Operator, I want the Utilities_Agent to analyze utility failures (e.g., broken water pipes, power outages) and propose repair and public safety actions, so that service restoration is coordinated effectively.

#### Acceptance Criteria

1. WHEN a UTILITIES-categorized Incident is received, THE Utilities_Agent SHALL retrieve utility network maps, service area data, and repair crew availability from the Knowledge_Base.
2. WHEN the Utilities_Agent has completed retrieval, THE Utilities_Agent SHALL identify the affected service area, the estimated number of impacted residents, and the repair complexity rated as LOW, MEDIUM, or HIGH based on the scope of the affected network segment.
3. WHEN the Utilities_Agent has completed its assessment, THE Utilities_Agent SHALL generate Recommendations for repair crew dispatch, temporary service alternatives, and public notification.
4. WHEN the Utilities_Agent has completed its assessment, THE Utilities_Agent SHALL produce a Communication_Draft for the relevant utility operator and for public notification channels.
5. IF the utility failure affects assets tagged in the Knowledge_Base as serving hospitals or emergency services, THEN THE Utilities_Agent SHALL escalate the Severity_Level to CRITICAL.
6. THE Utilities_Agent SHALL complete its analysis and produce both the Recommendations list and the Communication_Draft within 60 seconds of receiving the Incident.
7. IF the Knowledge_Base is unavailable when the Utilities_Agent attempts retrieval, THEN THE Utilities_Agent SHALL proceed using only the Incident data provided, note each unavailable data source by name in its output, and continue analysis.
8. IF the Utilities_Agent has not produced complete output within 60 seconds, THEN THE Utilities_Agent SHALL emit a partial output containing all analysis completed to that point, with an indication that the output is incomplete, and continue processing.

---

### Requirement 9: Specialist Agent Analysis — Public Services

**User Story:** As a Human_Operator, I want the PublicServices_Agent to analyze disruptions to public sector services and propose continuity and communication actions, so that citizens are informed and services are restored.

#### Acceptance Criteria

1. WHEN a PUBLIC_SERVICES-categorized Incident is received, THE PublicServices_Agent SHALL retrieve service dependency maps, alternative service locations, and citizen communication templates from the Knowledge_Base; IF any of these data sources is unavailable, THEN THE PublicServices_Agent SHALL proceed with the available data and note each unavailable source by name in its output.
2. WHEN the PublicServices_Agent has completed retrieval, THE PublicServices_Agent SHALL identify the affected services, the impacted citizen groups per affected service, and the estimated restoration timeline expressed as a duration in hours or days per service.
3. WHEN the PublicServices_Agent has completed its assessment, THE PublicServices_Agent SHALL generate Recommendations containing at minimum one service continuity measure and one citizen communication action per affected service.
4. WHEN the PublicServices_Agent has completed its assessment, THE PublicServices_Agent SHALL produce a Communication_Draft for each affected service's responsible department, including the list of affected services, the estimated restoration timeline, and available alternative access options.
5. THE PublicServices_Agent SHALL complete its analysis and produce both the Recommendations list and the Communication_Draft within 60 seconds of receiving the Incident.
6. IF the PublicServices_Agent has not produced complete output within 60 seconds, THEN THE PublicServices_Agent SHALL emit a timeout notification to the Human_Operator identifying which outputs are incomplete, preserve all partial outputs produced to that point, and continue processing.

---

### Requirement 10: Result Aggregation and Summary

**User Story:** As a Human_Operator, I want a consolidated summary of all specialist agent outputs, so that I can review the full picture and make a decision efficiently.

#### Acceptance Criteria

1. WHEN all activated Specialist_Agents have completed their analysis, THE Aggregator_Agent SHALL consolidate their outputs into a single Incident Summary.
2. THE Aggregator_Agent SHALL include in the Incident Summary: incident details, classification, Severity_Level, all Recommendations ordered from highest to lowest Severity_Level, all Communication_Drafts, and a list of proposed next actions.
3. WHEN all activated Specialist_Agents have completed their analysis, THE Aggregator_Agent SHALL present the Incident Summary to the Human_Operator via the System's user interface within 10 seconds.
4. IF one or more Specialist_Agents fail to respond within 30 seconds of their allotted time, THEN THE Aggregator_Agent SHALL produce a partial summary that identifies each non-responding agent by name and proceed to present the summary to the Human_Operator.
5. WHEN the Incident Summary is complete, THE Aggregator_Agent SHALL log the complete Incident Summary to the Observability_Platform.

---

### Requirement 11: Human-in-the-Loop Decision and Approval

**User Story:** As a Human_Operator, I want to review, modify, approve, or reject the System's recommendations before any action is taken, so that final decisions always rest with me.

#### Acceptance Criteria

1. WHEN a Recommendation or Communication_Draft is generated, THE System SHALL present it to the Human_Operator for review before any external communication or action is dispatched.
2. WHEN the Human_Operator approves a Recommendation, THE System SHALL record the approval with a timestamp and the operator's identifier.
3. WHEN the Human_Operator rejects a Recommendation, THE System SHALL record the rejection with a reason and allow the Human_Operator to request a revised Recommendation, up to a maximum of 3 revision cycles per Recommendation.
4. WHEN the Human_Operator modifies a Recommendation or Communication_Draft, THE System SHALL preserve both the original version and the modified version in the audit log.
5. THE System SHALL dispatch approved Communication_Drafts only after explicit Human_Operator approval.
6. WHILE awaiting Human_Operator review, THE System SHALL display an elapsed time counter in minutes and seconds indicating the time since the Incident was first reported.
7. IF the Human_Operator has not acted on a presented Recommendation or Communication_Draft within 30 minutes of it being presented, THEN THE System SHALL escalate the Incident to the next available Human_Operator or supervisor and notify both parties.

*v1.0 note:* Chainlit supports per-recommendation approve/reject and Submit; dispatch is simulated. Edit-in-UI and 30-minute supervisor escalation are not fully implemented.

---

### Requirement 12: Configurable LLM Models per Agent

**User Story:** As a system administrator, I want to configure a different LLM model for each Specialist_Agent, so that I can optimize performance, cost, and capability per crisis domain.

#### Acceptance Criteria

1. THE System SHALL support an Agent_Config file that specifies, for each agent, the LLM provider (NVIDIA NIM or local LLM), model name, temperature, max_tokens, and top_p inference parameters.
2. WHEN the System starts, THE Orchestrator SHALL load each agent's Agent_Config and initialize the corresponding LLM client.
3. IF an Agent_Config entry is missing for a Specialist_Agent, THEN THE Orchestrator SHALL apply the system-level default NVIDIA NIM model configuration defined in the global defaults section of the Agent_Config file for that agent.
4. WHEN a valid Agent_Config file is saved while the System is running, THE Orchestrator SHALL reload the updated configuration and apply it to subsequent agent invocations without requiring a full system restart.
5. WHERE a local LLM is configured for an agent, THE System SHALL route inference requests to the local endpoint specified in the Agent_Config.
6. IF the Agent_Config file contains a malformed entry for a Specialist_Agent, THEN THE Orchestrator SHALL log an error identifying the malformed entry by agent name and field, apply the system-level default configuration for that agent, and continue startup.
7. IF a local LLM endpoint specified in the Agent_Config is unreachable at invocation time, THEN THE System SHALL log the connectivity failure, fall back to the system-level default NVIDIA NIM model for that agent invocation, and notify the system administrator.
8. WHEN an agent is invoked, THE System SHALL log the model name and provider used for that invocation to the Observability_Platform.

*v1.0 note:* Models are configured in `configs/llm/multimodel.yaml`; workflow YAML in `configs/agents/`. **Restart** (`make restart`) required after config changes (acceptance 4 deferred).

---

### Requirement 13: Observability and Audit Logging

**User Story:** As a system administrator, I want full observability into agent interactions and decisions, so that I can audit, debug, and improve the System over time.

#### Acceptance Criteria

1. THE System SHALL integrate with the Observability_Platform to trace, for each agent call, the invocation identity, input payload, output payload, latency in milliseconds, timestamp, and agent name.
2. THE System SHALL log all Incident lifecycle events (creation, classification, routing, analysis, aggregation, Human_Operator decisions) with timestamps to a persistent audit log; IF the Observability_Platform is unavailable, THE System SHALL continue processing Incidents and buffer lifecycle events locally, flushing them to the Observability_Platform when it becomes available.
3. WHEN an agent produces an error or exception, THE System SHALL log the agent name, error type, error message, and the input that triggered the error to the Observability_Platform and continue processing with the remaining agents.
4. THE System SHALL retain audit logs for a minimum of 90 days.
5. THE System SHALL provide a query interface for the Human_Operator and administrators to retrieve historical Incident records and audit trails; IF record retrieval is temporarily unavailable, THE System SHALL keep the query interface accessible and return an error message indicating the cause and estimated resolution time.
6. IF the Observability_Platform is unavailable, THE System SHALL buffer up to 10,000 lifecycle events locally before discarding the oldest events, and SHALL notify the system administrator when the buffer reaches 80% capacity.

*v1.0 note:* Langfuse v3 traces per incident; Postgres stores incidents. Long-retention query UI and event buffer are partial.

---

### Requirement 14: Escalation and Multi-Agent Collaboration

**User Story:** As a Human_Operator, I want the System to automatically escalate complex incidents to additional agents and flag them for my attention, so that no critical detail is missed.

#### Acceptance Criteria

1. WHEN a Specialist_Agent determines that an Incident contains findings outside its designated domain and requires analysis from a different domain to produce a complete assessment, THE Specialist_Agent SHALL trigger an Escalation to the Router to activate the relevant additional Specialist_Agent.
2. WHEN an Escalation is triggered, THE Router SHALL activate the additional Specialist_Agent and pass the current Incident state, including all prior analysis outputs produced by previously activated Specialist_Agents.
3. WHILE the current Escalation chain depth is fewer than 3 levels, THE System SHALL permit further automatic Escalation triggers from Specialist_Agents.
4. IF an Escalation is triggered and the current Escalation chain depth has reached 3 levels, THEN THE System SHALL halt further automatic Escalation, notify the Human_Operator with an indication that the maximum escalation depth has been reached, and preserve the Incident state at that point for Human_Operator review.
5. WHEN an Escalation occurs, THE System SHALL notify the Human_Operator within 30 seconds with the domain mismatch reason that triggered the Escalation and the identifiers of all Specialist_Agents activated for the Incident up to that point.
6. IF the Router attempts to activate an additional Specialist_Agent during an Escalation and that agent is unavailable, THEN THE System SHALL notify the Human_Operator with an indication that the required Specialist_Agent could not be activated and preserve the current Incident state for Human_Operator review.
7. THE Aggregator_Agent SHALL incorporate the analysis outputs from all Specialist_Agents activated during the Escalation chain into the final Incident Summary before the Summary is marked complete.

*v1.0 note:* **Subagent** workflows (e.g. flood → comms) cover in-workflow child agents; full Router re-escalation is deferred.

---

### Requirement 15: System Resilience and Fault Tolerance

**User Story:** As a Human_Operator, I want the System to remain operational and informative even when individual agents fail, so that crisis response is never fully blocked by a technical failure.

#### Acceptance Criteria

1. IF a Specialist_Agent fails or does not respond within 30 seconds, THEN THE Orchestrator SHALL retry the agent invocation once, waiting up to 5 seconds before the retry, before marking it as failed.
2. IF a Specialist_Agent fails after retry, THEN THE Orchestrator SHALL continue the workflow with the remaining agents and include a failure notice in the Incident Summary that identifies the failed agent by name and indicates that its output is unavailable.
3. THE System SHALL remain operational for Incident ingestion and routing, meaning it SHALL continue to accept new Incident_Reports and activate available Specialist_Agents, even when one or more Specialist_Agents are unavailable.
4. WHEN the System recovers from a partial failure, THE Orchestrator SHALL resume any in-progress Incident workflows from the last successfully completed workflow step recorded in the persistent state store.
5. THE System SHALL expose a health check endpoint that reports the operational status of each agent and the Orchestrator as one of: operational, degraded, or unavailable.

*v1.0 note:* Partial failure and `/health` implemented; explicit retry-once and LangGraph checkpointer resume are partial.
