"""Shared project paths and file helpers for research tools."""

from __future__ import annotations

from pathlib import Path

from cursor_agent_core.paths.file_helpers import (
    ensure_dir,
    relative_to_project,
    resolve_under_root,
    sanitize_filename,
    slugify,
    unique_path,
    utc_timestamp,
)
from cursor_agent_core.paths.project_context import (
    get_project_root,
    set_output_directory_resolver,
    set_project_root,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "Docs"
RESEARCH_DIR = DOCS_DIR / "Research"
PAPERS_DIR = DOCS_DIR / "Papers"
REPORTS_DIR = DOCS_DIR / "Reports"
DIAGRAMS_DIR = DOCS_DIR / "Diagrams"
SLIDES_DIR = DOCS_DIR / "Slides"
MISSIONS_DIR = DOCS_DIR / "Missions"

set_project_root(PROJECT_ROOT)


def papers_directory() -> Path:
    return ensure_dir(PAPERS_DIR)


def reports_directory() -> Path:
    return ensure_dir(REPORTS_DIR)


def diagrams_directory() -> Path:
    return ensure_dir(DIAGRAMS_DIR)


def slides_directory() -> Path:
    return ensure_dir(SLIDES_DIR)


def missions_directory() -> Path:
    return ensure_dir(MISSIONS_DIR)


def research_directory() -> Path:
    return ensure_dir(RESEARCH_DIR)


def _active_session_or_none():
    from deep_research.session_context import get_active_session

    return get_active_session()


def session_root() -> Path | None:
    session = _active_session_or_none()
    return session.root if session else None


def _resolve_output_kind(kind: str) -> Path:
    session = _active_session_or_none()
    if session:
        mapping = {
            "papers": session.papers_dir,
            "reports": session.reports_dir,
            "diagrams": session.diagrams_dir,
            "slides": session.slides_dir,
        }
        factory = mapping.get(kind)
        if factory:
            return factory()

    fallback = {
        "papers": papers_directory,
        "reports": reports_directory,
        "diagrams": diagrams_directory,
        "slides": slides_directory,
    }
    fn = fallback.get(kind)
    if fn:
        return fn()
    return ensure_dir(DOCS_DIR / kind.title())


set_output_directory_resolver(_resolve_output_kind)


def active_papers_directory() -> Path:
    return _resolve_output_kind("papers")


def active_reports_directory() -> Path:
    return _resolve_output_kind("reports")


def active_diagrams_directory() -> Path:
    return _resolve_output_kind("diagrams")


def active_slides_directory() -> Path:
    return _resolve_output_kind("slides")


def resolve_project_path(path_str: str) -> Path:
    """Resolve a project-relative or absolute path under PROJECT_ROOT."""
    return resolve_under_root(path_str, PROJECT_ROOT)


def relative_to_project_path(path: Path) -> str:
    return relative_to_project(path, PROJECT_ROOT)
