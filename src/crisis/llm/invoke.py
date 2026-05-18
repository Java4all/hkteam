"""LangChain chat invoke with optional Langfuse callbacks from pipeline context."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from crisis.observability.langfuse import get_active_invoke_config


def _merge_runnable_config(
    base: dict[str, Any] | None, extra: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not base and not extra:
        return None
    if not base:
        return dict(extra) if extra else None
    if not extra:
        return dict(base)
    merged = dict(base)
    base_cbs = list(merged.get("callbacks") or [])
    extra_cbs = list(extra.get("callbacks") or [])
    if base_cbs or extra_cbs:
        merged["callbacks"] = base_cbs + extra_cbs
    meta = dict(merged.get("metadata") or {})
    meta.update(extra.get("metadata") or {})
    if meta:
        merged["metadata"] = meta
    for key, value in extra.items():
        if key not in ("callbacks", "metadata"):
            merged[key] = value
    return merged


def invoke_chat(
    llm: BaseChatModel,
    messages: list[BaseMessage] | str,
    *,
    config: dict[str, Any] | None = None,
    **kwargs: Any,
):
    """Invoke chat model; attach Langfuse CallbackHandler when pipeline session is active."""
    run_config = _merge_runnable_config(get_active_invoke_config(), config)
    if run_config:
        return llm.invoke(messages, config=run_config, **kwargs)
    return llm.invoke(messages, **kwargs)
