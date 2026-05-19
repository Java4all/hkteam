from __future__ import annotations

from crisis.settings import settings
from crisis.store.memory import MemoryIncidentStore

_store = None


def get_incident_store():
    global _store
    if _store is not None:
        return _store
    if settings.database_url:
        from crisis.store.postgres import PostgresIncidentStore

        _store = PostgresIncidentStore(settings.database_url)
    else:
        _store = MemoryIncidentStore()
    return _store


class _StoreProxy:
    """Lazy store — Postgres when DATABASE_URL is set, else in-memory (tests)."""

    def save_pipeline_result(self, state):
        return get_incident_store().save_pipeline_result(state)

    def get(self, incident_id: str):
        return get_incident_store().get(incident_id)

    def record_human_decision(self, incident_id: str, decision):
        return get_incident_store().record_human_decision(incident_id, decision)

    def list_ids(self):
        return get_incident_store().list_ids()

    def list_summaries(self, limit: int = 50):
        return get_incident_store().list_summaries(limit)


incident_store = _StoreProxy()
