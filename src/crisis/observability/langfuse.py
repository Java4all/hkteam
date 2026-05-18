from __future__ import annotations

import logging
import os
from typing import Any

from crisis.settings import settings

logger = logging.getLogger(__name__)

_client_ready = False


def _langfuse_base_url() -> str:
    return (settings.langfuse_base_url or settings.langfuse_host).rstrip("/")


def _langfuse_credentials() -> tuple[str, str] | None:
    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key
    if not public_key or not secret_key:
        return None
    return public_key, secret_key


def _apply_langfuse_env() -> None:
    """Langfuse SDK v3 reads credentials from env; set before get_client / CallbackHandler."""
    base = _langfuse_base_url()
    creds = _langfuse_credentials()
    if creds:
        public_key, secret_key = creds
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        os.environ["LANGFUSE_SECRET_KEY"] = secret_key
    os.environ["LANGFUSE_HOST"] = base
    os.environ["LANGFUSE_BASE_URL"] = base


def _ensure_langfuse_client() -> bool:
    """Register the Langfuse singleton with explicit pk/sk (required for CallbackHandler)."""
    global _client_ready
    if _client_ready:
        return True
    creds = _langfuse_credentials()
    if not creds:
        return False
    public_key, secret_key = creds
    if not public_key.startswith("pk-lf-") or not secret_key.startswith("sk-lf-"):
        logger.warning(
            "Langfuse keys should start with pk-lf- / sk-lf- — copy a fresh pair from the UI"
        )
    try:
        from langfuse import Langfuse

        _apply_langfuse_env()
        Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=_langfuse_base_url(),
        )
        _client_ready = True
        return True
    except Exception as exc:
        logger.warning("failed to initialize Langfuse client: %s", exc)
        return False


def get_langfuse_client():
    from langfuse import get_client

    if not _ensure_langfuse_client():
        raise RuntimeError("Langfuse client not configured (missing or invalid LANGFUSE_* keys)")
    return get_client()


def flush_langfuse_traces() -> None:
    """Push batched traces (required in Docker/FastAPI — otherwise UI stays empty)."""
    if not settings.langfuse_enabled:
        return
    if not _langfuse_credentials():
        return
    try:
        get_langfuse_client().flush()
    except Exception as exc:
        logger.warning("langfuse flush failed: %s", exc)


def get_langfuse_config(*, session_id: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """LangGraph invoke config with Langfuse callback when enabled."""
    if not settings.langfuse_enabled:
        return {}
    if not _langfuse_credentials():
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

    if not _ensure_langfuse_client():
        return {}
    try:
        handler = CallbackHandler()
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

    creds = _langfuse_credentials()
    if creds:
        public_key, _secret_key = creds
        out["public_key_prefix"] = public_key[:12] + "..." if len(public_key) > 12 else public_key
        try:
            client = get_langfuse_client()
            out["auth_ok"] = bool(client.auth_check())
        except Exception as exc:
            out["auth_ok"] = False
            out["auth_error"] = str(exc)
    else:
        out["auth_ok"] = False
        out["auth_note"] = "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env"

    return out
