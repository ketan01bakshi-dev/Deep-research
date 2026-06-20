"""Follow-up mission behavior tests."""

from __future__ import annotations

from cursor_agent_core.runtime.types import AgentResult

from deep_research.autonomous import run_follow_up_mission
from deep_research.autonomous_mission import ResearchMission
from deep_research.session_context import create_session, load_session


def _session_env(monkeypatch, tmp_path):
    research = tmp_path / "Research"
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", research)
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", research)


def test_follow_up_cancelled_turn_marks_session_cancelled(monkeypatch, tmp_path):
    _session_env(monkeypatch, tmp_path)
    mission = ResearchMission(
        topic="Follow-up cancel",
        field="science",
        objectives=["Test"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="completed")

    cancelled = AgentResult(
        question="prompt",
        answer=None,
        session_id="agent-1",
        num_turns=0,
        total_cost_usd=None,
        is_error=True,
        subtype="error_during_execution",
        error="Cancelled by user",
    )
    monkeypatch.setattr("deep_research.autonomous._run_agent_mission", lambda *args, **kwargs: cancelled)

    result = run_follow_up_mission(
        session.id,
        "Please continue",
        ["answer"],
        should_cancel=lambda: True,
    )

    assert result.subtype == "cancelled"
    assert result.error == "Cancelled by user"
    assert load_session(session.id).status == "cancelled"
