"""Tests for Deep Research mission validation and deliverables."""

from __future__ import annotations

from pathlib import Path

import pytest

from deep_research.autonomous_mission import (
    ResearchMission,
    build_mission_prompt,
    validate_mission,
    verify_deliverables,
)
from deep_research.session_context import (
    MAX_LINKED_SESSIONS,
    clear_active_session,
    create_session,
    get_session_context_bundle,
    load_session,
    set_active_session,
)


def test_validate_mission_requires_deliverables():
    mission = ResearchMission(
        topic="Test topic",
        field="general",
        objectives=["Explore test topic"],
        deliverables=[],
    )
    result = validate_mission(mission)
    assert not result.ok
    assert result.clarification_message


def test_validate_mission_normalizes_aliases():
    mission = ResearchMission(
        topic="Protein digestion",
        field="health",
        objectives=["Explain digestion"],
        deliverables=["summary", "docx", "pdf"],
    )
    result = validate_mission(mission)
    assert result.ok
    assert result.mission is not None
    normalized = result.mission.normalized_deliverables()
    assert "answer" in normalized
    assert "report" in normalized
    assert "papers" in normalized


def test_verify_deliverables_answer(tmp_path, monkeypatch):
    from deep_research.tools import paths as tool_paths

    monkeypatch.setattr(tool_paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tool_paths, "RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr(
        "deep_research.session_context.RESEARCH_DIR",
        tmp_path / "Research",
    )
    monkeypatch.setattr(
        "deep_research.session_context.PROJECT_ROOT",
        tmp_path,
    )

    mission = ResearchMission(
        topic="Cache test",
        field="science",
        objectives=["Test objectives"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="running")
    missing = verify_deliverables(mission, answer="")
    assert "answer" in missing

    missing_ok = verify_deliverables(mission, answer="Synthesized findings here.")
    assert "answer" not in missing_ok
    loaded = load_session(session.id)
    assert loaded.topic == "Cache test"


def test_verify_deliverables_paper_summary(tmp_path, monkeypatch):
    from deep_research.tools import paths as tool_paths

    monkeypatch.setattr(tool_paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tool_paths, "RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)

    mission = ResearchMission(
        topic="Summary test",
        field="science",
        objectives=["Summarize"],
        deliverables=["paper_summary"],
    )
    session = create_session(mission, status="running")
    from deep_research.session_context import set_active_session

    set_active_session(session)
    missing = verify_deliverables(mission, answer="ok")
    assert "paper_summary" in missing

    summaries = session.root / "Papers" / "summaries"
    summaries.mkdir(parents=True)
    (summaries / "paper_summary.md").write_text("# Summary", encoding="utf-8")
    missing_ok = verify_deliverables(mission, answer="ok")
    assert "paper_summary" not in missing_ok
    clear_active_session()


def test_verify_deliverables_all_artifact_types(tmp_path, monkeypatch):
    from deep_research.tools import paths as tool_paths

    monkeypatch.setattr(tool_paths, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tool_paths, "RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)

    mission = ResearchMission(
        topic="Artifact test",
        field="science",
        objectives=["Create artifacts"],
        deliverables=["answer", "report", "mindmap", "slides", "papers", "paper_summary"],
    )
    session = create_session(mission, status="running")
    set_active_session(session)

    missing = verify_deliverables(mission, answer="")
    assert set(missing) == {"answer", "report", "mindmap", "slides", "papers", "paper_summary"}

    (session.reports_dir() / "report.md").write_text("# Report", encoding="utf-8")
    (session.diagrams_dir() / "map.png").write_text("png", encoding="utf-8")
    (session.slides_dir() / "slides.pptx").write_text("pptx", encoding="utf-8")
    (session.papers_dir() / "paper.pdf").write_text("pdf", encoding="utf-8")
    summaries = session.root / "Papers" / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    (summaries / "summary.md").write_text("# Summary", encoding="utf-8")

    assert verify_deliverables(mission, answer="Done") == []
    clear_active_session()


def test_build_mission_prompt_includes_follow_up_and_health_disclaimer():
    mission = ResearchMission(
        topic="Diabetes research",
        field="health",
        objectives=["Explain"],
        deliverables=["answer"],
    )
    prompt = build_mission_prompt(mission, follow_up_prompt="Focus on beta cells.")

    assert "## Follow-up request" in prompt
    assert "Focus on beta cells." in prompt
    assert "not personal medical advice" in prompt


def test_context_bundle_respects_link_limit():
    bundle = get_session_context_bundle(["a", "b", "c", "d"])
    assert "Prior research context" in bundle
    assert MAX_LINKED_SESSIONS == 3
