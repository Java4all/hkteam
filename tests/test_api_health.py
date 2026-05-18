import os

os.environ["DATABASE_URL"] = ""
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["CRISIS_USE_MOCK_LLM"] = "true"

from fastapi.testclient import TestClient

from crisis.api.main import app

client = TestClient(app)


def test_health_live_is_fast():
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_default_skips_nvidia_probe():
    r = client.get("/health")
    assert r.status_code == 200
    assert "note" in r.json()["nvidia"]
