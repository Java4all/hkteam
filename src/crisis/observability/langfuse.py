from __future__ import annotations

import logging
import os
from typing import Any

from crisis.settings import settings

logger = logging.getLogger(__name__)


def _apply_langfuse_env() -> None:
    """Langfuse SDK v3+ reads credentials from env (not CallbackHandler kwargs)."""
    if settings.langfuse_public_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    if settings.langfuse_secret_key:
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    if settings.langfuse_host:
        os.environ["LANGFUSE_HOST"] = settings.langfuse_host.rstrip("/")


def get_langfuse_config(*, session_id: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """LangGraph invoke config with Langfuse callback when enabled."""
    if not settings.langfuse_enabled:
        return {}
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse enabled but LANGFUSE_PUBLIC_KEY/SECRET_KEY not set — tracing skipped")
        return {}
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError as exc:
        logger.warning(
            "langfuse callback not available (%s). Install: pip install langchain langfuse",
            exc,
        )
        return {}

    _apply_langfuse_env()
    try:
        handler = CallbackHandler(public_key=settings.langfuse_public_key)
    except Exception as exc:
        logger.warning("failed to create Langfuse CallbackHandler: %s", exc)
        return {}

    config: dict[str, Any] = {"callbacks": [handler]}
    metadata: dict[str, Any] = {}
    if session_id:
        metadata["langfuse_session_id"] = session_id
    tag_list = list(tags or ["smart-city-crisis"])
    metadata["langfuse_tags"] = tag_list
    config["metadata"] = metadata
    return config


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
