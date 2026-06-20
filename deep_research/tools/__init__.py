"""Custom research tools for the deep-research agent."""

from __future__ import annotations

import os

from cursor_sdk import CustomTool

from cursor_agent_core.outputs.diagrams import CREATE_DIAGRAM_TOOL
from cursor_agent_core.outputs.registry import build_output_tools
from cursor_agent_core.outputs.reports import CREATE_REPORT_TOOL as CREATE_RESEARCH_REPORT_TOOL
from cursor_agent_core.outputs.slides import CREATE_SLIDE_DECK_TOOL
from deep_research.tools.complete_mission import COMPLETE_MISSION_TOOL
from deep_research.tools.paper_summary import SUMMARIZE_PAPERS_TOOL
from deep_research.tools.pdf_enhanced import DOWNLOAD_PDFS_ENHANCED_TOOL
from deep_research.tools.rag_tool import QUERY_SESSION_CORPUS_TOOL
from deep_research.tools.source_verify import VERIFY_SOURCES_TOOL
from deep_research.tools.tavily_search import SEARCH_RESEARCH_LITERATURE_TOOL

__all__ = [
    "COMPLETE_MISSION_TOOL",
    "CREATE_DIAGRAM_TOOL",
    "CREATE_RESEARCH_REPORT_TOOL",
    "CREATE_SLIDE_DECK_TOOL",
    "DOWNLOAD_RESEARCH_PDFS_TOOL",
    "QUERY_SESSION_CORPUS_TOOL",
    "SEARCH_RESEARCH_LITERATURE_TOOL",
    "SUMMARIZE_PAPERS_TOOL",
    "build_all_custom_tools",
    "build_research_custom_tools",
]

DOWNLOAD_RESEARCH_PDFS_TOOL = DOWNLOAD_PDFS_ENHANCED_TOOL


def build_all_custom_tools() -> dict[str, CustomTool]:
    """
    Return all host-side custom tools for the deep-research agent.

    Output tools come from cursor_agent_core. Tavily search tools are added when
    TAVILY_API_KEY is configured.
    """
    tools: dict[str, CustomTool] = {
        "complete_mission": COMPLETE_MISSION_TOOL,
        "summarize_downloaded_papers": SUMMARIZE_PAPERS_TOOL,
        "query_session_corpus": QUERY_SESSION_CORPUS_TOOL,
        **build_output_tools(),
    }

    if os.environ.get("TAVILY_API_KEY", "").strip():
        tools["search_research_literature"] = SEARCH_RESEARCH_LITERATURE_TOOL
        tools["download_research_pdfs"] = DOWNLOAD_PDFS_ENHANCED_TOOL
        tools["verify_sources"] = VERIFY_SOURCES_TOOL

    return tools


def build_research_custom_tools() -> dict[str, CustomTool] | None:
    """Backward-compatible alias; returns None only when no tools are available."""
    tools = build_all_custom_tools()
    return tools or None
