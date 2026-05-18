from __future__ import annotations

from urllib.parse import urlparse

from crisis.settings import settings

_HOSTED = frozenset({"integrate.api.nvidia.com", "ai.api.nvidia.com"})


def is_hosted_nim_url(base_url: str) -> bool:
    try:
        return urlparse(base_url).netloc in _HOSTED
    except Exception:
        return False


def nvidia_api_key_configured() -> bool:
    key = (settings.nvidia_api_key or "").strip()
    return bool(key) and key not in {"x", "nvapi-..."}


def nvidia_health() -> dict:
    out: dict = {
        "configured": nvidia_api_key_configured(),
        "mock_llm": settings.crisis_use_mock_llm,
        "profile": settings.llm_profile,
        "base_url": settings.nim_cloud_base_url,
    }
    if settings.crisis_use_mock_llm:
        out["ok"] = True
        out["note"] = "CRISIS_USE_MOCK_LLM=true"
        return out
    if not out["configured"]:
        out["ok"] = False
        out["error"] = "Set NVIDIA_API_KEY in .env (nvapi-... from build.nvidia.com)"
        return out
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        llm = ChatNVIDIA(
            model="nvidia/nemotron-mini-4b-instruct",
            api_key=settings.nvidia_api_key.strip(),
            max_completion_tokens=8,
        )
        llm.invoke("ping")
        out["ok"] = True
        out["probe_model"] = "nvidia/nemotron-mini-4b-instruct"
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)
        if "404" in str(exc):
            out["hint"] = (
                "404 from integrate.api.nvidia.com — check NVIDIA_API_KEY and model IDs "
                "in configs/llm/multimodel.yaml; list models at GET /v1/models"
            )
    return out
