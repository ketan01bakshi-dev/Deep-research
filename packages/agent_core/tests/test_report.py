from __future__ import annotations

from agent_core.report import (
    render_report,
    report_header,
    section_empty_state,
    section_summary,
    section_warnings,
)


def test_render_report_joins_sections() -> None:
    report = render_report(
        [
            report_header("Test Report"),
            section_summary(["**Items:** 3"]),
            section_warnings(["source failed"]),
        ]
    )
    assert "# Test Report" in report
    assert "## Summary" in report
    assert "**Items:** 3" in report
    assert "## Warnings" in report
    assert "source failed" in report


def test_section_empty_state_includes_suggestions() -> None:
    section = section_empty_state("Alerts", "Nothing found.", ["Try again"])
    text = "\n".join(section)
    assert "## Alerts" in text
    assert "Nothing found." in text
    assert "Try again" in text
