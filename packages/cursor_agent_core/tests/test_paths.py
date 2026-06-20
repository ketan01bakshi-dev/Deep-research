"""Tests for cursor_agent_core path helpers."""

from pathlib import Path

from cursor_agent_core.paths.file_helpers import slugify, unique_path, ensure_dir


def test_slugify_basic() -> None:
    assert slugify("Hello World!") == "hello-world"


def test_unique_path_no_collision(tmp_path: Path) -> None:
    directory = ensure_dir(tmp_path / "out")
    first = unique_path(directory, "report.md")
    first.write_text("a", encoding="utf-8")
    second = unique_path(directory, "report.md")
    assert first != second
    assert second.name == "report_2.md"
