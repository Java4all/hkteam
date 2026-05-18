"""Smoke-test Langfuse from inside the api container: python -m crisis.observability.test_trace"""

from __future__ import annotations

import socket
import sys
from urllib.parse import urlparse

from crisis.observability.langfuse import _apply_langfuse_env, flush_langfuse_traces, langfuse_health
from crisis.settings import settings


def _host_from_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Invalid Langfuse URL: {url!r}")
    return parsed.hostname


def main() -> int:
    base = (settings.langfuse_base_url or settings.langfuse_host).rstrip("/")
    print("LANGFUSE_HOST / BASE_URL:", base)
    print("LANGFUSE_PUBLIC_KEY set:", bool(settings.langfuse_public_key))
    print("LANGFUSE_SECRET_KEY set:", bool(settings.langfuse_secret_key))

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        print("ERROR: Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env, then: make restart")
        return 1

    if "localhost" in base or "127.0.0.1" in base:
        print(
            "ERROR: LANGFUSE_HOST must be http://langfuse:3000 inside Docker (not localhost).\n"
            "       Fix .env and docker-compose api environment, then: make restart"
        )
        return 1

    host = _host_from_url(base)
    try:
        socket.getaddrinfo(host, 3000)
        print(f"DNS OK: {host}")
    except socket.gaierror as exc:
        print(f"ERROR: Cannot resolve {host!r} — is the langfuse service running?")
        print("       Run: docker compose ps langfuse && docker compose up -d langfuse")
        print(f"       ({exc})")
        return 1

    health = langfuse_health()
    print("health:", health)
    if not health.get("reachable"):
        print("ERROR: Langfuse /api/public/health not reachable from api container")
        return 1
    if not health.get("auth_ok"):
        print("ERROR: Langfuse auth_check failed — wrong API keys or project")
        return 1

    _apply_langfuse_env()
    from langfuse import get_client

    client = get_client(public_key=settings.langfuse_public_key)
    with client.start_as_current_span(name="smoke-test") as span:
        span.update(input={"hello": "world"}, output={"status": "ok"})
    flush_langfuse_traces()
    print("OK: smoke-test trace sent. Open Langfuse UI → Traces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
