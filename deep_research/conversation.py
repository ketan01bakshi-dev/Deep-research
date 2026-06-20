"""Stateful conversational research agent using the Cursor SDK."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from cursor_sdk import Agent, CursorAgentError

from deep_research.cursor_adapter import MessageHandler, run_agent_turn, run_resume_turn
from cursor_agent_core.bridge.client import cursor_client
from deep_research.cursor_options import build_agent_options, project_cwd
from deep_research.display import default_activity_handler
from deep_research.prompts import CONVERSATIONAL_RESEARCH_SYSTEM_PROMPT
from deep_research.types import ResearchResult


@dataclass(slots=True)
class ConversationResult:
    """Outcome of a full multi-turn research conversation."""

    example_id: str | None
    title: str | None
    session_id: str | None
    turns: list[ResearchResult] = field(default_factory=list)
    total_cost_usd: float = 0.0

    @property
    def is_error(self) -> bool:
        return any(turn.is_error for turn in self.turns)


class ConversationalResearchAgent:
    """
    Multi-turn health research agent with session memory.

    Uses Agent.create() so each ask() continues the same conversation. The SDK
    persists agent state locally; agent_id can be reused with resume_research().
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        max_turns: int | None = None,
        max_budget_usd: float | None = None,
        on_message: MessageHandler | None = default_activity_handler,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._max_turns = max_turns
        self._max_budget_usd = max_budget_usd
        self._on_message = on_message
        self._client_cm: Any = None
        self._cursor_client: Any = None
        self._agent: Any = None
        self._agent_cm: Any = None
        self._agent_id: str | None = None
        self._turn_results: list[ResearchResult] = []
        self._first_turn = True

    def __enter__(self) -> ConversationalResearchAgent:
        options = build_agent_options(model=self._model, api_key=self._api_key)
        try:
            self._client_cm = cursor_client(workspace=project_cwd())
            self._cursor_client = self._client_cm.__enter__()
            self._agent_cm = Agent.create(options, client=self._cursor_client)
            self._agent = self._agent_cm.__enter__()
            self._agent_id = self._agent.agent_id
        except CursorAgentError as exc:
            raise RuntimeError(str(exc.message)) from exc
        except OSError as exc:
            raise RuntimeError(f"Bridge launch failed: {exc}") from exc
        return self

    def __exit__(self, *exc: object) -> None:
        if self._agent_cm is not None:
            self._agent_cm.__exit__(*exc)
        if self._client_cm is not None:
            self._client_cm.__exit__(*exc)
        self._agent = None
        self._agent_cm = None
        self._cursor_client = None
        self._client_cm = None

    @property
    def session_id(self) -> str | None:
        return self._agent_id

    @property
    def turn_results(self) -> list[ResearchResult]:
        return list(self._turn_results)

    def ask(self, prompt: str) -> ResearchResult:
        """Send one turn; prior turns in this session remain in context."""
        if self._agent is None:
            raise RuntimeError("ConversationalResearchAgent is not connected. Use with block.")

        prefix = CONVERSATIONAL_RESEARCH_SYSTEM_PROMPT if self._first_turn else None
        self._first_turn = False

        result = run_agent_turn(
            self._agent,
            prompt,
            on_message=self._on_message,
            prefix_system=prefix,
        )
        if result.session_id:
            self._agent_id = result.session_id
        self._turn_results.append(result)
        return result

    def run_turns(
        self,
        prompts: Sequence[str],
        *,
        example_id: str | None = None,
        title: str | None = None,
    ) -> ConversationResult:
        """Run a scripted multi-turn conversation in one session."""
        turns: list[ResearchResult] = []

        for prompt in prompts:
            turn = self.ask(prompt)
            turns.append(turn)
            if turn.is_error:
                break

        return ConversationResult(
            example_id=example_id,
            title=title,
            session_id=self._agent_id,
            turns=turns,
            total_cost_usd=0.0,
        )


def resume_research(
    agent_id: str,
    prompt: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
    fork_session: bool = False,
    on_message: MessageHandler | None = default_activity_handler,
) -> ResearchResult:
    """
    Resume a persisted agent by ID (cross-process follow-up).

    Use the agent ID printed after a conversational run. cwd must match the
    directory used when the agent was created. fork_session is not supported
    by the Cursor SDK and is ignored.
    """
    _ = (max_turns, max_budget_usd, fork_session)
    return run_resume_turn(
        agent_id,
        prompt,
        model=model,
        api_key=api_key,
        on_message=on_message,
    )
