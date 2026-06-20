"""Shared result types for Cursor SDK agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentResult:
    """Outcome of a single agent query or conversational turn."""

    question: str
    answer: str | None
    session_id: str | None
    num_turns: int
    total_cost_usd: float | None
    is_error: bool
    subtype: str | None
    error: str | None = None
    messages: list[Any] = field(default_factory=list)
