"""Thin adapter between deep_research and the Cursor SDK."""

from __future__ import annotations

from cursor_agent_core.runtime.adapter import (
    MessageHandler,
    consume_run,
    error_result,
    handle_stream_message,
    prefix_prompt,
    run_agent_turn,
    run_stateless_prompt,
    run_to_result,
)
from cursor_agent_core.runtime.types import AgentResult as ResearchResult
from cursor_agent_core.runtime.adapter import run_resume_turn as _run_resume_turn
from deep_research.cursor_options import PROJECT_ROOT
from deep_research.tools import build_all_custom_tools
from deep_research.prompts import (
    CONVERSATIONAL_RESEARCH_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
)


def run_stateless_research(
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    on_message: MessageHandler | None = None,
) -> ResearchResult:
    """Phase 1: one-shot research via Agent.prompt()."""
    _ = on_message
    return run_stateless_prompt(
        prompt,
        system_prompt=RESEARCH_SYSTEM_PROMPT,
        project_root=str(PROJECT_ROOT),
        model=model,
        api_key=api_key,
        custom_tools=build_all_custom_tools(),
        default_model_env="RESEARCH_MODEL",
        fallback_model="composer-2.5",
    )


def run_resume_turn(
    agent_id: str,
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    on_message: MessageHandler | None = None,
    prefix_system: str | None = None,
) -> ResearchResult:
    """Resume a persisted agent by ID and send one follow-up."""
    return _run_resume_turn(
        agent_id,
        prompt,
        project_root=str(PROJECT_ROOT),
        model=model,
        api_key=api_key,
        custom_tools=build_all_custom_tools(),
        default_model_env="RESEARCH_MODEL",
        fallback_model="composer-2.5",
        on_message=on_message,
        prefix_system=prefix_system,
    )


__all__ = [
    "MessageHandler",
    "ResearchResult",
    "consume_run",
    "error_result",
    "handle_stream_message",
    "prefix_prompt",
    "run_agent_turn",
    "run_resume_turn",
    "run_stateless_research",
    "run_to_result",
]
