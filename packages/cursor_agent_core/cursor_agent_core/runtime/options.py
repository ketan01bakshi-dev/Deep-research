"""Cursor SDK AgentOptions builder."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from cursor_sdk import AgentOptions, CustomTool, LocalAgentOptions


def build_agent_options(
    *,
    project_root: Path | str,
    custom_tools: Mapping[str, CustomTool] | None = None,
    model: str | None = None,
    api_key: str | None = None,
    default_model_env: str = "AGENT_MODEL",
    fallback_model: str = "composer-2.5",
) -> AgentOptions:
    """Build AgentOptions for a local Cursor agent."""
    key = (api_key or os.environ.get("CURSOR_API_KEY", "")).strip()
    resolved_model = model or os.environ.get(default_model_env, fallback_model)
    cwd = str(Path(project_root).resolve())
    tools = dict(custom_tools or {})

    return AgentOptions(
        api_key=key or None,
        model=resolved_model,
        local=LocalAgentOptions(
            cwd=cwd,
            setting_sources=["project"],
            custom_tools=tools,
        ),
    )
