"""Pipeline cancellation behavior (no live Cursor API)."""

from __future__ import annotations

from deep_research.autonomous_mission import ResearchMission
from deep_research.pipeline import run_pipeline_mission


class _FakeAgentCtx:
    def __enter__(self):
        return object()

    def __exit__(self, *args):
        return False


class _FakeClientCtx:
    def __enter__(self):
        return object()

    def __exit__(self, *args):
        return False


class _FakeAgent:
    @staticmethod
    def create(options, client=None):
        return _FakeAgentCtx()


def _session_env(monkeypatch, tmp_path):
    research = tmp_path / "Research"
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", research)
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", research)


def _minimal_mission() -> ResearchMission:
    return ResearchMission(
        topic="Cancel test",
        field="science",
        objectives=["Verify cooperative cancel"],
        deliverables=["answer"],
    )


def test_pipeline_returns_cancelled_when_flag_set_before_phases(monkeypatch, tmp_path):
    _session_env(monkeypatch, tmp_path)
    monkeypatch.setattr("deep_research.pipeline.cursor_client", lambda **kw: _FakeClientCtx())
    monkeypatch.setattr("deep_research.pipeline.Agent", _FakeAgent)

    result = run_pipeline_mission(_minimal_mission(), should_cancel=lambda: True)

    assert result.is_error
    assert result.subtype == "cancelled"
    assert result.error == "Cancelled by user"
    assert result.session_id


def test_pipeline_cancel_during_retry_loop(monkeypatch, tmp_path):
    """Cancellation in the deliverable retry loop should mark session cancelled."""
    from cursor_agent_core.runtime.types import AgentResult
    from deep_research.session_context import load_session

    _session_env(monkeypatch, tmp_path)
    monkeypatch.setattr("deep_research.pipeline.cursor_client", lambda **kw: _FakeClientCtx())
    monkeypatch.setattr("deep_research.pipeline.Agent", _FakeAgent)

    ok_turn = AgentResult(
        question="Cancel test",
        answer="Partial answer",
        session_id="fake-session",
        num_turns=1,
        total_cost_usd=0.01,
        is_error=False,
        subtype="success",
        error=None,
    )
    cancel_checks = {"n": 0}

    def should_cancel():
        cancel_checks["n"] += 1
        # Four phase-loop checks, then cancel on first retry-loop check.
        return cancel_checks["n"] >= 5

    monkeypatch.setattr(
        "deep_research.pipeline._run_turn_cancellable",
        lambda *args, **kwargs: ok_turn,
    )
    monkeypatch.setattr(
        "deep_research.pipeline.verify_deliverables",
        lambda mission, answer: ["report"],
    )

    mission = ResearchMission(
        topic="Cancel test",
        field="science",
        objectives=["Retry cancel"],
        deliverables=["answer", "report"],
    )
    result = run_pipeline_mission(
        mission,
        max_completion_retries=2,
        should_cancel=should_cancel,
    )

    assert result.subtype == "cancelled"
    session = load_session(result.session_id)
    assert session.status == "cancelled"
