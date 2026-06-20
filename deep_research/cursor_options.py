"""Cursor SDK configuration for the deep-research agent."""

from __future__ import annotations

import os
from pathlib import Path

from cursor_sdk import AgentOptions, CustomTool

from cursor_agent_core.node.cli import set_node_project_root
from cursor_agent_core.paths.project_context import set_project_root
from cursor_agent_core.runtime.options import build_agent_options as _build_agent_options
from deep_research.tools import build_all_custom_tools

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = os.environ.get("RESEARCH_MODEL", "composer-2.5")

set_project_root(PROJECT_ROOT)
set_node_project_root(PROJECT_ROOT)


def project_cwd() -> str:
    """Workspace directory for local Cursor agents (must stay stable for resume)."""
    return str(PROJECT_ROOT)


def build_agent_options(
    *,
    model: str | None = None,
    api_key: str | None = None,
    custom_tools: dict[str, CustomTool] | None = None,
) -> AgentOptions:
    """Shared AgentOptions for stateless and conversational agents."""
    return _build_agent_options(
        project_root=PROJECT_ROOT,
        custom_tools=custom_tools or build_all_custom_tools(),
        model=model,
        api_key=api_key,
        default_model_env="RESEARCH_MODEL",
        fallback_model=DEFAULT_MODEL,
    )
