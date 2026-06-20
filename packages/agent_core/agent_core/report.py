"""Markdown report skeleton helpers."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def report_header(title: str, *, generated_at: datetime | None = None) -> list[str]:
    when = generated_at or datetime.now()
    return [
        f"# {title}",
        "",
        f"*Generated: {when.strftime('%Y-%m-%d %H:%M')}*",
        "",
    ]


def section_summary(bullets: list[str]) -> list[str]:
    lines = ["## Summary", ""]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.append("")
    return lines


def section_warnings(errors: list[str]) -> list[str]:
    if not errors:
        return []
    lines = ["## Warnings", ""]
    lines.extend(f"- {error}" for error in errors)
    lines.append("")
    return lines


def section_ranked(title: str, entries: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.extend(entries)
    lines.append("")
    return lines


def section_empty_state(title: str, message: str, suggestions: list[str]) -> list[str]:
    lines = [f"## {title}", "", message, ""]
    if suggestions:
        lines.append("**Suggestions:**")
        lines.extend(f"- {suggestion}" for suggestion in suggestions)
        lines.append("")
    return lines


def render_report(sections: list[list[str]]) -> str:
    lines: list[str] = []
    for section in sections:
        if section:
            lines.extend(section)
    return "\n".join(lines)


def publish_results(
    report_path: Path,
    latest_dir: Path,
    *,
    report_name: str = "report.md",
    artifacts: list[tuple[Path, str]] | None = None,
) -> None:
    latest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report_path, latest_dir / report_name)
    for src, dest_name in artifacts or []:
        if src.exists():
            shutil.copy2(src, latest_dir / dest_name)
