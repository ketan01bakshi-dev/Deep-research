"""Shared result types for research agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cursor_agent_core.runtime.types import AgentResult as ResearchResult

if TYPE_CHECKING:
    from deep_research.autonomous_mission import ResearchMission


@dataclass(slots=True)
class AutonomousResearchResult(ResearchResult):
    """Outcome of an autonomous mission run."""

    mission: ResearchMission | None = None
    artifacts: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    clarification_needed: bool = False
    missing_deliverables: list[str] = field(default_factory=list)


__all__ = ["AutonomousResearchResult", "ResearchResult"]
