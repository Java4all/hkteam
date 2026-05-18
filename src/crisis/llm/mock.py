"""Deterministic LLM for demo tests and offline presentations."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class MockCrisisLLM(BaseChatModel):
    agent_id: str = "general"
    role: str = "agent"

    @property
    def _llm_type(self) -> str:
        return "mock-crisis-llm"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any) -> ChatResult:
        text = messages[-1].content if messages else ""
        content = self._mock_content(text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _mock_content(self, prompt: str) -> str:
        if self.role in ("classifier", "router"):
            return json.dumps(
                {
                    "categories": ["UTILITIES"],
                    "severity": "HIGH",
                    "confidence": 0.85,
                    "hints": ["water_main"],
                }
            )
        if self.role == "aggregator":
            return (
                "## Incident overview\n"
                "Multi-agent analysis completed (mock mode).\n\n"
                "## Ranked actions\n"
                "1. Dispatch utilities repair crew to reported location.\n"
                "2. Issue public notification for service disruption.\n\n"
                "## Conflicts\n"
                "None identified in mock run.\n"
            )
        agent = self.agent_id
        return (
            f"## Summary\n"
            f"{agent.title()} specialist assessment (mock LLM).\n\n"
            f"## Recommendations\n"
            f"- Secure the area and confirm scope [{agent}]\n"
            f"- Coordinate with city operations center\n\n"
            f"## Communication draft\n"
            f"Audience: city services | Priority: HIGH\n"
            f"Preliminary alert for incident at location in report.\n\n"
            f"## Evidence\n"
            f"- knowledge_base.md (mock)\n"
        )
