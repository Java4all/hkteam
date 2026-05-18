from __future__ import annotations

from crisis.llm.nvidia_client import build_chat_model, package_versions, probe_cloud_chat
from crisis.llm.nvidia_urls import HOSTED_CLOUD_BASE
from crisis.settings import settings


def nvidia_api_key_configured() -> bool:
    key = (settings.nvidia_api_key or "").strip()
    return bool(key) and key not in {"x", "nvapi-..."}


def nvidia_health() -> dict:
    out: dict = {
        "configured": nvidia_api_key_configured(),
        "mock_llm": settings.crisis_use_mock_llm,
        "profile": settings.llm_profile,
        "base_url": settings.nim_cloud_base_url or HOSTED_CLOUD_BASE,
        "packages": package_versions(),
        "client": "langchain_openai.BaseChatOpenAI (hosted) / ChatNVIDIA (local NIM)",
    }
    if settings.crisis_use_mock_llm:
        out["ok"] = True
        out["note"] = "CRISIS_USE_MOCK_LLM=true"
        return out
    if not out["configured"]:
        out["ok"] = False
        out["error"] = "Set NVIDIA_API_KEY in .env (nvapi-... from build.nvidia.com)"
        return out

    probe_model = "nvidia/nemotron-mini-4b-instruct"
    key = settings.nvidia_api_key.strip()
    out["http_probe"] = probe_cloud_chat(model=probe_model, api_key=key)

    try:
        llm = build_chat_model(
            model=probe_model,
            base_url=settings.nim_cloud_base_url,
            api_key=key,
            temperature=0.1,
            max_tokens=8,
        )
        llm.invoke("ping")
        out["ok"] = True
        out["probe_model"] = probe_model
    except Exception as exc:
        out["ok"] = False
        out["error"] = str(exc)
        http = out.get("http_probe") or {}
        if http.get("ok"):
            out["hint"] = "HTTP probe succeeded but LangChain client failed — rebuild api image (pip install -e .)"
        elif http.get("status_code") == 401:
            out["hint"] = "Invalid NVIDIA_API_KEY — regenerate at build.nvidia.com"
        elif http.get("status_code") == 403:
            out["hint"] = "Key valid format but forbidden — enable model on build.nvidia.com for this account"
        elif http.get("status_code") == 404 or "404" in str(exc):
            out["hint"] = (
                "404 — check NIM_CLOUD_BASE_URL=https://integrate.api.nvidia.com/v1 in .env; "
                "rebuild api: docker compose --env-file .env build --no-cache api"
            )
        elif "max_completion_tokens" in str(exc) or "extra_forbidden" in str(exc):
            out["hint"] = "LangChain sent max_completion_tokens — rebuild api image (needs BaseChatOpenAI fix)"
    return out
