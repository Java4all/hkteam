from __future__ import annotations

import logging
from typing import Any

from crisis.settings import settings

logger = logging.getLogger(__name__)


def get_langfuse_config(*, session_id: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """LangGraph invoke config with Langfuse callback when enabled."""
    if not settings.langfuse_enabled:
        return {}
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY not set — tracing skipped")
        return {}
    try:
        from langfuse.callback import CallbackHandler
    except ImportError:
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError as exc:
            logger.warning("langfuse callback not available: %s", exc)
            return {}

    handler = CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host.rstrip("/"),
        session_id=session_id,
        tags=tags or ["smart-city-crisis"],
    )
    return {"callbacks": [handler]}


def langfuse_health() -> dict[str, Any]:
    if not settings.langfuse_enabled:
        return {"enabled": False}
    try:
        import httpx

        url = f"{settings.langfuse_host.rstrip('/')}/api/public/health"
        r = httpx.get(url, timeout=3.0)
        return {"enabled": True, "reachable": r.status_code == 200, "status_code": r.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "error": str(exc)}
