"""Register shared output custom tools."""

from __future__ import annotations

from cursor_sdk import CustomTool

from cursor_agent_core.outputs.diagrams import CREATE_DIAGRAM_TOOL
from cursor_agent_core.outputs.pdf_download import DOWNLOAD_PDFS_TOOL
from cursor_agent_core.outputs.reports import CREATE_REPORT_TOOL
from cursor_agent_core.outputs.slides import CREATE_SLIDE_DECK_TOOL


def build_output_tools() -> dict[str, CustomTool]:
    """Return output custom tools (reports, diagrams, slides, PDF download)."""
    return {
        "create_diagram": CREATE_DIAGRAM_TOOL,
        "create_slide_deck": CREATE_SLIDE_DECK_TOOL,
        "create_research_report": CREATE_REPORT_TOOL,
        "download_research_pdfs": DOWNLOAD_PDFS_TOOL,
    }
