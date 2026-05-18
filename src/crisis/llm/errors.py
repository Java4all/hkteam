from __future__ import annotations


def is_llm_timeout(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "timed out" in msg or "timeout" in msg:
        return True
    name = type(exc).__name__.lower()
    return "timeout" in name
