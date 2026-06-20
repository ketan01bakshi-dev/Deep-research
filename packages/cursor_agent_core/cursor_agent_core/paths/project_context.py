"""Project root and output directory context for custom tools."""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path

_project_root: ContextVar[Path | None] = ContextVar("project_root", default=None)
_output_resolver: ContextVar[Callable[[str], Path] | None] = ContextVar(
    "output_resolver",
    default=None,
)

OUTPUT_KINDS = frozenset({"reports", "diagrams", "slides", "papers"})


def set_project_root(root: Path | str) -> None:
    _project_root.set(Path(root).resolve())


def get_project_root() -> Path:
    root = _project_root.get()
    if root is None:
        raise RuntimeError("Project root not set. Call set_project_root() first.")
    return root


def set_output_directory_resolver(resolver: Callable[[str], Path]) -> None:
    """Register resolver mapping kind (reports/diagrams/slides/papers) to directory."""
    _output_resolver.set(resolver)


def get_output_directory(kind: str) -> Path:
    """Return output directory for a kind, using resolver or Docs/{Kind}/ fallback."""
    kind = kind.lower()
    resolver = _output_resolver.get()
    if resolver is not None:
        return resolver(kind)

    root = get_project_root()
    folder_names = {
        "reports": "Reports",
        "diagrams": "Diagrams",
        "slides": "Slides",
        "papers": "Papers",
    }
    name = folder_names.get(kind, kind.title())
    from cursor_agent_core.paths.file_helpers import ensure_dir

    return ensure_dir(root / "Docs" / name)
