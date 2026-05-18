from __future__ import annotations

import logging
import os
from typing import Any

from crisis.settings import settings

logger = logging.getLogger(__name__)


def _langfuse_base_url() -> str:
    return (settings.langfuse_base_url or settings.langfuse_host).rstrip("/")


def _apply_langfuse_env() -> None:
    """Langfuse SDK v3+ reads credentials from env (not CallbackHandler kwargs)."""
    base = _langfuse_base_url()
    if settings.langfuse_public_key:
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    if settings.langfuse_secret_key:
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = base
    os.environ["LANGFUSE_BASE_URL"] = base


def flush_langfuse_traces() -> None:
    """Push batched traces (required in Docker/FastAPI — otherwise UI stays empty)."""
    if not settings.langfuse_enabled:
        return
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return
    try:
        from langfuse import get_client

        _apply_langfuse_env()
        get_client(public_key=settings.langfuse_public_key).flush()
    except Exception as exc:
        logger.warning("langfuse flush failed: %s", exc)


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
    base = _langfuse_base_url()
    out: dict[str, Any] = {"enabled": True, "host": base}
    try:
        import httpx

        r = httpx.get(f"{base}/api/public/health", timeout=3.0)
        out["reachable"] = r.status_code == 200
        out["status_code"] = r.status_code
    except Exception as exc:
        out["reachable"] = False
        out["error"] = str(exc)

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import get_client

            _apply_langfuse_env()
            client = get_client(public_key=settings.langfuse_public_key)
            out["auth_ok"] = bool(client.auth_check())
        except Exception as exc:
            out["auth_ok"] = False
            out["auth_error"] = str(exc)
    else:
        out["auth_ok"] = False
        out["auth_note"] = "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env"

    return out
