"""Custom tool behavior tests without live network calls."""

from __future__ import annotations

import json

import pytest

from deep_research.autonomous_mission import ResearchMission
from deep_research.session_context import clear_active_session, create_session, set_active_session


def _session_env(monkeypatch, tmp_path):
    research = tmp_path / "Research"
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", research)
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", research)
    monkeypatch.setattr("deep_research.rag.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.source_verify.PROJECT_ROOT", tmp_path)
    return research


def _active_session(monkeypatch, tmp_path):
    _session_env(monkeypatch, tmp_path)
    mission = ResearchMission(
        topic="Tool test",
        field="science",
        objectives=["Test tools"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="running")
    set_active_session(session)
    return session


def test_complete_mission_writes_completion_json(monkeypatch, tmp_path):
    from deep_research.tools.complete_mission import complete_mission

    session = _active_session(monkeypatch, tmp_path)
    payload = json.loads(
        complete_mission(
            {
                "title": "Tool test",
                "summary": "Completed",
                "artifacts": ["Docs/Research/file.md"],
                "assumptions": ["Assumed scope"],
                "success_criteria_met": True,
            },
            None,
        )
    )

    completion = json.loads((session.root / "completion.json").read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["artifact_count"] == 1
    assert completion["summary"] == "Completed"
    assert completion["assumptions"] == ["Assumed scope"]
    clear_active_session()


def test_verify_sources_uses_head_check_and_updates_sources(monkeypatch, tmp_path):
    from deep_research.tools import source_verify

    session = _active_session(monkeypatch, tmp_path)

    def fake_head(url: str, *, timeout: float = 8.0):
        return {"url": url, "ok": "good" in url, "status": 200 if "good" in url else 404}

    monkeypatch.setattr(source_verify, "_head_check", fake_head)
    result = json.loads(
        source_verify.verify_sources(
            {"urls": ["https://example.com/good", "https://example.com/bad"]},
            None,
        )
    )

    assert result["verified_count"] == 1
    assert result["dead_links"] == ["https://example.com/bad"]
    saved = json.loads((session.root / "sources.json").read_text(encoding="utf-8"))
    assert saved["count"] == 2
    clear_active_session()


def test_query_session_corpus_tool_requires_active_session():
    from deep_research.tools.rag_tool import query_session_corpus_tool

    clear_active_session()
    with pytest.raises(ValueError, match="No active research session"):
        query_session_corpus_tool({"question": "anything"}, None)


def test_build_all_custom_tools_respects_tavily_env(monkeypatch):
    from deep_research.tools import build_all_custom_tools

    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    no_key = build_all_custom_tools()
    assert "complete_mission" in no_key
    assert "search_research_literature" not in no_key

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    with_key = build_all_custom_tools()
    assert "search_research_literature" in with_key
    assert "verify_sources" in with_key


def test_build_and_query_session_corpus(monkeypatch, tmp_path):
    from deep_research.rag import build_session_corpus, query_session_corpus
    from deep_research.session_context import update_session

    session = _active_session(monkeypatch, tmp_path)
    report = session.reports_dir() / "findings.md"
    report.write_text(
        " ".join(["Beta cell regeneration and insulin sensitivity evidence."] * 30),
        encoding="utf-8",
    )
    update_session(
        session.id,
        answer=" ".join(["Durable remission depends on beta cell function."] * 30),
    )

    index = build_session_corpus(session.id)
    hits = query_session_corpus(session.id, "beta cell remission", top_k=2)

    assert index["chunk_count"] >= 1
    assert hits
    assert any("beta" in hit["text"].lower() for hit in hits)
    clear_active_session()
