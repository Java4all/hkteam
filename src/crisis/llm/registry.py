from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from crisis.config.loader import load_llm_profile
from crisis.llm.mock import MockCrisisLLM
from crisis.llm.nvidia_client import build_chat_model
from crisis.llm.nvidia_health import nvidia_api_key_configured
from crisis.settings import settings


@dataclass(frozen=True)
class LlmProfile:
    profile_id: str
    provider: str
    base_url: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048
    tags: dict[str, str] | None = None

    @property
    def llm_provider(self) -> str:
        if self.tags:
            return self.tags.get("llm_provider", "unknown")
        return "local" if "127.0.0.1" in self.base_url or "localhost" in self.base_url else "cloud"


def _profile_from_dict(profile_id: str, raw: dict[str, Any]) -> LlmProfile:
    return LlmProfile(
        profile_id=profile_id,
        provider=str(raw.get("provider", "nim")),
        base_url=str(raw.get("base_url") or settings.nim_cloud_base_url),
        model=str(raw.get("model", "nvidia/nemotron-mini-4b-instruct")),
        temperature=float(raw.get("temperature", 0.2)),
        max_tokens=int(raw.get("max_tokens", 2048)),
        tags=raw.get("tags"),
    )


@lru_cache
def _llm_config() -> dict[str, Any]:
    return load_llm_profile()


def resolve_profile(agent_id: str | None = None, role: str = "agent") -> LlmProfile:
    cfg = _llm_config()
    profiles = cfg.get("profiles") or {}
    assignments = cfg.get("assignments") or {}
    profile_id: str | None = None

    if agent_id and "agents" in assignments:
        profile_id = (assignments.get("agents") or {}).get(agent_id)
    if not profile_id:
        profile_id = assignments.get(role) or assignments.get("workflow_selector_default")

    if not profile_id or profile_id not in profiles:
        profile_id = next(iter(profiles), "cloud_nemotron_mini")

    return _profile_from_dict(profile_id, profiles[profile_id])


def get_llm(agent_id: str | None = None, role: str = "agent") -> BaseChatModel:
    if settings.crisis_use_mock_llm:
        return MockCrisisLLM(agent_id=agent_id or "general", role=role)

    if not nvidia_api_key_configured():
        raise RuntimeError(
            "NVIDIA_API_KEY is missing or still a placeholder. Set nvapi-... in .env "
            "or CRISIS_USE_MOCK_LLM=true for offline smoke tests."
        )

    profile = resolve_profile(agent_id, role)
    return build_chat_model(
        model=profile.model,
        base_url=profile.base_url,
        api_key=settings.nvidia_api_key,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
    )
