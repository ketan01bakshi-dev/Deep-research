"""Shared Cursor SDK infrastructure for D:\\Agents SDK agents."""

from cursor_agent_core.bridge.client import cursor_client
from cursor_agent_core.bridge.windows_compat import apply_windows_compat
from cursor_agent_core.runtime.adapter import (
    MessageHandler,
    consume_run,
    error_result,
    handle_stream_message,
    prefix_prompt,
    run_agent_turn,
    run_resume_turn,
    run_stateless_prompt,
    run_to_result,
)
from cursor_agent_core.runtime.console import configure_stdio
from cursor_agent_core.runtime.options import build_agent_options
from cursor_agent_core.runtime.types import AgentResult

__all__ = [
    "AgentResult",
    "MessageHandler",
    "apply_windows_compat",
    "build_agent_options",
    "configure_stdio",
    "consume_run",
    "cursor_client",
    "error_result",
    "handle_stream_message",
    "prefix_prompt",
    "run_agent_turn",
    "run_resume_turn",
    "run_stateless_prompt",
    "run_to_result",
]
