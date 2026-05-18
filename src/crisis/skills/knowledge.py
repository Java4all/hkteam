from __future__ import annotations

from pathlib import Path

from crisis.settings import settings


def _read_kb() -> str:
    path = settings.data_dir / "knowledge_base.md"
    if not path.exists():
        return "(no knowledge base loaded)"
    return path.read_text(encoding="utf-8")[:4000]


def enrich_agent_context(agent_id: str, description: str, location: str, hints: list[str]) -> tuple[str, list[dict]]:
    kb = _read_kb()
    network = settings.data_dir / "utilities_network.json"
    extra = ""
    if agent_id == "utilities" and network.exists():
        extra = network.read_text(encoding="utf-8")[:2000]
    blob = (
        f"## knowledge_base\n{kb}\n\n"
        f"## incident\nlocation: {location}\ndescription: {description}\n"
        f"hints: {', '.join(hints)}\n\n"
        f"## agent_data\n{extra}\n"
    )
    evidence = [
        {"id": "ev-kb", "source": "knowledge_base.md", "excerpt": kb[:400]},
    ]
    if extra:
        evidence.append({"id": "ev-network", "source": "utilities_network.json", "excerpt": extra[:400]})
    return blob, evidence
