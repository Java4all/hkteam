import os

os.environ["LANGFUSE_ENABLED"] = "false"

from crisis.llm.invoke import invoke_chat
from crisis.llm.mock import MockCrisisLLM
from crisis.observability.langfuse import get_active_invoke_config, langfuse_incident_session


def test_invoke_chat_without_session_has_no_config():
    llm = MockCrisisLLM(agent_id="cyber", role="agent")
    assert get_active_invoke_config() is None
    invoke_chat(llm, "ping")


def test_langfuse_session_sets_active_config(monkeypatch):
    captured: list[dict | None] = []

    def fake_get_langfuse_config(**kwargs):
        captured.append(kwargs)
        return {"callbacks": ["mock-handler"], "metadata": {"langfuse_session_id": kwargs.get("session_id")}}

    monkeypatch.setattr(
        "crisis.observability.langfuse.get_langfuse_config",
        fake_get_langfuse_config,
    )
    monkeypatch.setattr("crisis.observability.langfuse.flush_langfuse_traces", lambda: None)
    monkeypatch.setattr(
        "crisis.observability.langfuse._ensure_langfuse_client",
        lambda: True,
    )

    with langfuse_incident_session("INC-TEST-1", tags=["test"]):
        assert get_active_invoke_config() is not None
        assert get_active_invoke_config()["metadata"]["langfuse_session_id"] == "INC-TEST-1"
    assert get_active_invoke_config() is None
    assert captured[0]["session_id"] == "INC-TEST-1"
