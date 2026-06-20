"""Generic filesystem helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*]+')
_SLUG_INVALID = re.compile(r"[^a-z0-9_-]+")


def ensure_dir(path: Path) -> Path:
    """Create directory if missing and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(text: str, *, max_length: int = 80) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.strip().lower()
    slug = _SLUG_INVALID.sub("-", slug.replace(" ", "-"))
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        slug = "untitled"
    return slug[:max_length]


def sanitize_filename(name: str, *, fallback: str = "file") -> str:
    """Strip invalid filename characters."""
    cleaned = _INVALID_CHARS.sub("_", name).strip("._ ")
    return cleaned or fallback


def unique_path(directory: Path, filename: str) -> Path:
    """Return a non-colliding path inside directory."""
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def relative_to_project(path: Path, project_root: Path) -> str:
    """Return a project-relative path string."""
    return str(path.relative_to(project_root))


def resolve_under_root(path_str: str, project_root: Path) -> Path:
    """Resolve a project-relative or absolute path under project_root."""
    path = Path(path_str)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (project_root / path).resolve()
    root = project_root.resolve()
    if root not in resolved.parents and resolved != root:
        raise ValueError(f"Path must be inside project root: {path_str}")
    return resolved


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
