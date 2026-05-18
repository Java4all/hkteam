"""Build chat clients for NVIDIA cloud (OpenAI-compatible) or local NIM."""

from __future__ import annotations

import importlib.metadata
import os
from urllib.parse import urlparse

import httpx
from langchain_core.language_models.chat_models import BaseChatModel

from crisis.llm.nvidia_urls import HOSTED_CLOUD_BASE, is_hosted_nim_url
from crisis.settings import settings


def normalize_cloud_base_url(url: str) -> str:
    """Ensure integrate URL includes /v1 (required for chat/completions)."""
    resolved = (url or settings.nim_cloud_base_url or HOSTED_CLOUD_BASE).strip().rstrip("/")
    if not resolved:
        return HOSTED_CLOUD_BASE
    if is_hosted_nim_url(resolved) and not resolved.endswith("/v1"):
        return f"{resolved}/v1"
    return resolved


def build_chat_model(
    *,
    model: str,
    base_url: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: float | None = None,
    max_retries: int = 1,
) -> BaseChatModel:
    """Hosted cloud uses OpenAI-compatible client; local NIM uses ChatNVIDIA."""
    api_key = api_key.strip()
    os.environ["NVIDIA_API_KEY"] = api_key

    req_timeout = timeout if timeout is not None else settings.crisis_llm_timeout
    base = normalize_cloud_base_url(base_url)
    if is_hosted_nim_url(base):
        # BaseChatOpenAI (not ChatOpenAI): integrate.api.nvidia.com requires max_tokens,
        # not max_completion_tokens which ChatOpenAI adds in newer langchain-openai.
        from langchain_openai.chat_models.base import BaseChatOpenAI

        return BaseChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=req_timeout,
            max_retries=max_retries,
        )

    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    return ChatNVIDIA(
        model=model,
        api_key=api_key,
        base_url=base,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        timeout=req_timeout,
    )


def probe_cloud_chat(*, model: str, api_key: str, base_url: str | None = None) -> dict:
    """Direct HTTP probe (bypasses LangChain) for clearer errors in diagnostics."""
    base = normalize_cloud_base_url(base_url or HOSTED_CLOUD_BASE)
    url = f"{base}/chat/completions"
    try:
        r = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
            },
            timeout=60.0,
        )
        return {
            "ok": r.status_code == 200,
            "status_code": r.status_code,
            "url": url,
            "body_preview": (r.text or "")[:300],
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("langchain-openai", "langchain-nvidia-ai-endpoints", "openai"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return versions
