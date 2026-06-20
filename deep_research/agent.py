"""Stateless research agent using the Cursor SDK."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from deep_research.cursor_adapter import MessageHandler, run_stateless_research
from deep_research.display import default_activity_handler, format_result_summary
from deep_research.types import ResearchResult

__all__ = [
    "MessageHandler",
    "ResearchResult",
    "default_activity_handler",
    "format_result_summary",
    "run_research",
]


def run_research(
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    on_message: MessageHandler | None = default_activity_handler,
) -> ResearchResult:
    """
    Run one stateless research query.

    Each call starts a fresh agent with no memory of previous queries (phase 1).
    max_turns and max_budget_usd are accepted for CLI compatibility but not enforced
    by the Cursor SDK.
    """
    _ = (max_turns, max_budget_usd, on_message)
    return run_stateless_research(
        prompt,
        model=model,
        api_key=api_key,
    )
