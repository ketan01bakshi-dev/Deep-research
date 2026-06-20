"""Deep-research agent built on the Cursor SDK."""

from deep_research.agent import run_research
from deep_research.autonomous import AutonomousResearchAgent, run_autonomous_mission
from deep_research.autonomous_examples import AUTONOMOUS_MISSION_EXAMPLES
from deep_research.autonomous_mission import ResearchMission, mission_from_dict, mission_from_json
from deep_research.conversation import (
    ConversationalResearchAgent,
    ConversationResult,
    resume_research,
)
from deep_research.conversation_examples import CONVERSATION_EXAMPLES
from deep_research.examples import HEALTH_RESEARCH_EXAMPLES
from deep_research.types import AutonomousResearchResult, ResearchResult

__all__ = [
    "AUTONOMOUS_MISSION_EXAMPLES",
    "AutonomousResearchAgent",
    "AutonomousResearchResult",
    "CONVERSATION_EXAMPLES",
    "ConversationalResearchAgent",
    "ConversationResult",
    "HEALTH_RESEARCH_EXAMPLES",
    "ResearchMission",
    "ResearchResult",
    "mission_from_dict",
    "mission_from_json",
    "resume_research",
    "run_autonomous_mission",
    "run_research",
]
