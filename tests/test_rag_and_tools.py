"""Tests for RAG and paper_summary deliverable."""

from __future__ import annotations

from deep_research.autonomous_mission import ResearchMission, validate_mission
from deep_research.rag import _tokenize, format_corpus_context, query_session_corpus


def test_paper_summary_deliverable_normalized():
    mission = ResearchMission(
        topic="Battery tech",
        field="materials",
        objectives=["Review papers"],
        deliverables=["paper_summaries"],
    )
    result = validate_mission(mission)
    assert result.ok
    assert "paper_summary" in result.mission.normalized_deliverables()


def test_rag_tokenize_and_empty_query():
    tokens = _tokenize("Solid state battery electrolytes 2025")
    assert "solid" in tokens
    assert "battery" in tokens
    assert format_corpus_context([]) == ""


def test_tavily_cache_key_stable():
    from deep_research.tools.search_support import _cache_key

    a = _cache_key("query", "academic", 10, "year")
    b = _cache_key("query", "academic", 10, "year")
    assert a == b
    assert _cache_key("other", "academic", 10, "year") != a
