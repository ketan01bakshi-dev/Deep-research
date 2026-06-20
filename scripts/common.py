"""Shared paths and env loading for Deep Research scripts."""

from __future__ import annotations

from pathlib import Path

from agent_core import load_agent_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
RESEARCH_DIR = DOCS_DIR / "Research"
MISSIONS_DIR = PROJECT_ROOT / "missions"


def bootstrap_env() -> Path:
    """Load .env and return project root."""
    load_agent_env(PROJECT_ROOT)
    return PROJECT_ROOT
