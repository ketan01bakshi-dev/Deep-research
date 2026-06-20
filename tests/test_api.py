"""HTTP API smoke and contract tests."""

from __future__ import annotations

import inspect
import os

from fastapi.testclient import TestClient


def _isolated_registry(api_main, monkeypatch, tmp_path):
    from deep_research.run_registry import RunRegistry

    registry = RunRegistry(persist_path=tmp_path / "jobs.json")
    monkeypatch.setattr(api_main, "JOBS_PATH", tmp_path / "jobs.json")
    monkeypatch.setattr(api_main, "_registry", registry)


def test_api_health():
    from apps.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "cursor_api_key" in body


def test_api_mission_request_requires_topic():
    from apps.api.main import app

    client = TestClient(app)
    response = client.post("/missions", json={"field": "science"})
    assert response.status_code == 422


def test_api_auth_required_when_key_configured(monkeypatch, tmp_path):
    from apps.api import main as api_main

    _isolated_registry(api_main, monkeypatch, tmp_path)
    monkeypatch.setenv("DEEP_RESEARCH_API_KEY", "secret-key")
    client = TestClient(api_main.app)
    assert client.post("/missions", json={"topic": "Auth test", "deliverables": ["answer"]}).status_code == 401
    response = client.post(
        "/missions",
        json={"topic": "Auth test", "deliverables": ["answer"]},
        headers={"Authorization": "Bearer secret-key"},
    )
    assert response.status_code == 200


def test_api_job_runner_accepts_pipeline_flag(monkeypatch, tmp_path):
    from apps.api import main as api_main
    from deep_research.run_registry import RunRecord
    from deep_research.types import AutonomousResearchResult

    _isolated_registry(api_main, monkeypatch, tmp_path)
    captured: dict = {}

    def fake_pipeline(mission, **kwargs):
        captured["runner"] = "pipeline"
        captured["kwargs"] = kwargs
        return AutonomousResearchResult(
            question=mission.topic,
            answer="ok",
            session_id="sess-2",
            num_turns=1,
            total_cost_usd=0.0,
            is_error=False,
            subtype="success",
            mission=mission,
        )

    monkeypatch.setattr(api_main, "run_pipeline_mission", fake_pipeline)
    run = RunRecord(id="job-1", kind="mission", label="Test")
    result = api_main._run_job(
        run,
        {
            "topic": "API pipeline",
            "field": "science",
            "objectives": ["Test"],
            "deliverables": ["answer"],
            "use_pipeline": True,
            "max_retries": 2,
        },
    )

    assert captured["runner"] == "pipeline"
    assert captured["kwargs"]["max_completion_retries"] == 2
    assert callable(captured["kwargs"]["should_cancel"])
    assert result.session_id == "sess-2"


def test_run_pipeline_mission_signature_matches_api_usage():
    from deep_research.pipeline import run_pipeline_mission

    params = inspect.signature(run_pipeline_mission).parameters
    assert "max_completion_retries" in params
    assert "should_cancel" in params
    assert params["should_cancel"].default is None


def test_api_mission_lifecycle_with_mock_runner(monkeypatch, tmp_path):
    from apps.api import main as api_main
    from deep_research.types import AutonomousResearchResult

    _isolated_registry(api_main, monkeypatch, tmp_path)

    def fake_runner(mission, **kwargs):
        return AutonomousResearchResult(
            question=mission.topic,
            answer="api answer",
            session_id="session-api",
            num_turns=1,
            total_cost_usd=0.0,
            is_error=False,
            subtype="success",
            mission=mission,
        )

    monkeypatch.setattr(api_main, "run_autonomous_mission", fake_runner)
    client = TestClient(api_main.app)
    response = client.post("/missions", json={"topic": "API", "deliverables": ["answer"]})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    run = api_main._registry.get(job_id)
    run._thread.join(timeout=2)
    status = client.get(f"/missions/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["session_id"] == "session-api"
    assert api_main.JOBS_PATH.exists()


def test_api_cancel_endpoint(monkeypatch, tmp_path):
    from apps.api import main as api_main

    _isolated_registry(api_main, monkeypatch, tmp_path)
    run = api_main._registry.create("mission", "Cancel", run_id="job-cancel")
    run.status = "running"
    response = TestClient(api_main.app).post("/missions/job-cancel/cancel")
    assert response.status_code == 200
    assert response.json()["cancel_requested"] is True
    assert run.should_cancel()


def test_api_export_streaming(monkeypatch, tmp_path):
    from apps.api import main as api_main

    _isolated_registry(api_main, monkeypatch, tmp_path)
    monkeypatch.setattr(api_main, "export_session_zip_enhanced", lambda sid: b"PK\x03\x04test")
    client = TestClient(api_main.app)
    response = client.get("/sessions/test-session/export?stream=true")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content.startswith(b"PK")


def test_api_missing_job_404():
    from apps.api.main import app

    client = TestClient(app)
    assert client.get("/missions/missing").status_code == 404
    assert client.post("/missions/missing/cancel").status_code == 404
