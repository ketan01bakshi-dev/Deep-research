"""Autonomous research agent — executes missions without mid-run questions."""

from __future__ import annotations

from typing import Any

from cursor_sdk import Agent, CursorAgentError

from deep_research.autonomous_mission import (
    ResearchMission,
    build_mission_prompt,
    collect_artifacts,
    validate_mission,
    verify_deliverables,
)
from deep_research.autonomous_prompts import system_prompt_for_field
from cursor_agent_core.bridge.client import cursor_client
from cursor_agent_core.runtime.adapter import (
    error_result,
    handle_stream_message,
    prefix_prompt,
    run_agent_turn,
    run_resume_turn,
    run_to_result,
)
from deep_research.cursor_adapter import MessageHandler
from deep_research.cursor_options import build_agent_options, project_cwd
from deep_research.display import default_activity_handler
from datetime import datetime, timezone

from collections.abc import Callable

from deep_research.session_context import (
    SessionTurn,
    append_activity,
    append_turn,
    clear_active_session,
    create_session,
    get_session_context_bundle,
    load_completion,
    load_session,
    load_turns,
    publish_session_to_latest,
    set_active_session,
    update_session,
)
from deep_research.types import AutonomousResearchResult


def _clarification_result(
    mission: ResearchMission,
    message: str,
) -> AutonomousResearchResult:
    return AutonomousResearchResult(
        question=mission.topic,
        answer=message,
        session_id=None,
        num_turns=0,
        total_cost_usd=None,
        is_error=False,
        subtype="clarification_needed",
        mission=mission,
        clarification_needed=True,
    )


def _validation_error_result(
    mission: ResearchMission | None,
    errors: list[str],
) -> AutonomousResearchResult:
    topic = mission.topic if mission else "unknown"
    return AutonomousResearchResult(
        question=topic,
        answer=None,
        session_id=None,
        num_turns=0,
        total_cost_usd=None,
        is_error=True,
        subtype="validation_error",
        error="; ".join(errors),
        mission=mission,
    )


def _build_continuation_prompt(mission: ResearchMission, missing: list[str]) -> str:
    return (
        f"Continue mission '{mission.topic}' without asking questions.\n"
        f"Missing deliverables: {', '.join(missing)}.\n"
        "Create only the missing artifacts, then call complete_mission again."
    )


def _merge_results(
    mission: ResearchMission,
    turn: Any,
    *,
    missing: list[str],
    research_session_id: str,
) -> AutonomousResearchResult:
    artifacts = collect_artifacts(mission)
    assumptions: list[str] = []
    completion = load_completion(research_session_id)
    if completion:
        assumptions = [str(a) for a in (completion.get("assumptions") or []) if str(a).strip()]
    return AutonomousResearchResult(
        question=mission.topic,
        answer=turn.answer,
        session_id=research_session_id,
        num_turns=turn.num_turns,
        total_cost_usd=turn.total_cost_usd,
        is_error=turn.is_error,
        subtype=turn.subtype,
        error=turn.error,
        messages=turn.messages,
        mission=mission,
        artifacts=artifacts,
        assumptions=assumptions,
        missing_deliverables=missing,
        clarification_needed=False,
    )


def _run_turn_cancellable(
    agent: Any,
    prompt: str,
    *,
    on_message: MessageHandler | None,
    prefix_system: str | None,
    should_cancel: Callable[[], bool] | None,
) -> Any:
    """Send one agent turn, stopping message consumption when should_cancel is set."""
    message = prefix_prompt(prompt, prefix_system) if prefix_system else prompt
    messages: list[Any] = []

    try:
        run = agent.send(message)
        for stream_message in run.messages():
            if should_cancel and should_cancel():
                return error_result(
                    prompt,
                    error="Cancelled by user",
                    agent_id=getattr(agent, "agent_id", None),
                    messages=messages,
                )
            messages.append(stream_message)
            handle_stream_message(stream_message, on_message)
        run_result = run.wait()
    except CursorAgentError as exc:
        return error_result(
            prompt,
            error=str(exc.message),
            agent_id=getattr(agent, "agent_id", None),
            messages=messages,
        )

    return run_to_result(
        prompt,
        agent_id=getattr(agent, "agent_id", None),
        run_result=run_result,
        messages=messages,
    )


def _prior_context_for_session(session_id: str) -> str:
    session = load_session(session_id)
    link_ids = list(session.linked_sessions)
    if session.parent_session_id and session.parent_session_id not in link_ids:
        link_ids.insert(0, session.parent_session_id)
    return get_session_context_bundle(link_ids)


def _turns_context(session_id: str) -> str:
    turns = load_turns(session_id)
    if not turns:
        return ""
    lines = ["## Current session turn history"]
    for index, turn in enumerate(turns, start=1):
        lines.append(f"\n### Turn {index}")
        lines.append(f"**Request:** {turn.prompt}")
        if turn.answer:
            preview = turn.answer[:1500]
            if len(turn.answer) > 1500:
                preview += "..."
            lines.append(f"**Answer:** {preview}")
    return "\n".join(lines)


def _persist_turn(
    session_id: str,
    *,
    prompt: str,
    answer: str | None,
    deliverables: list[str],
    is_error: bool,
    error: str | None,
    agent_id: str | None,
    num_turns: int,
    total_cost_usd: float | None,
) -> None:
    append_turn(
        session_id,
        SessionTurn(
            prompt=prompt,
            answer=answer,
            at=datetime.now(timezone.utc).isoformat(),
            deliverables=deliverables,
            is_error=is_error,
            error=error,
        ),
    )
    update_session(
        session_id,
        answer=answer,
        agent_id=agent_id,
        num_turns=num_turns,
        total_cost_usd=total_cost_usd,
        status="error" if is_error else "completed",
        error=error,
    )


def _run_agent_mission(
    mission: ResearchMission,
    prompt: str,
    *,
    model: str | None,
    api_key: str | None,
    max_completion_retries: int,
    on_message: MessageHandler | None,
    resume_agent_id: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> Any:
    if resume_agent_id:
        if should_cancel and should_cancel():
            return error_result(
                prompt,
                error="Cancelled by user",
                agent_id=resume_agent_id,
            )
        return run_resume_turn(
            resume_agent_id,
            prompt,
            model=model,
            api_key=api_key,
            on_message=on_message,
        )

    options = build_agent_options(model=model, api_key=api_key)
    with cursor_client(workspace=project_cwd()) as client:
        with Agent.create(options, client=client) as agent:
            turn = _run_turn_cancellable(
                agent,
                prompt,
                on_message=on_message,
                prefix_system=system_prompt_for_field(mission.field),
                should_cancel=should_cancel,
            )

            if turn.is_error and turn.error == "Cancelled by user":
                return turn

            retries = 0
            while retries < max_completion_retries:
                missing = verify_deliverables(mission, answer=turn.answer)
                if not missing or turn.is_error:
                    break
                if should_cancel and should_cancel():
                    return error_result(
                        prompt,
                        error="Cancelled by user",
                        agent_id=getattr(agent, "agent_id", None),
                        messages=turn.messages,
                    )
                retries += 1
                continuation = _build_continuation_prompt(mission, sorted(missing))
                turn = _run_turn_cancellable(
                    agent,
                    continuation,
                    on_message=on_message,
                    prefix_system=None,
                    should_cancel=should_cancel,
                )
                if turn.is_error and turn.error == "Cancelled by user":
                    return turn

            return turn


class AutonomousResearchAgent:
    """Runs a structured research mission to completion without user interaction."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        max_completion_retries: int = 1,
        on_message: MessageHandler | None = default_activity_handler,
        linked_sessions: list[str] | None = None,
        parent_session_id: str | None = None,
        session_id: str | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._max_completion_retries = max(0, max_completion_retries)
        self._on_message = on_message
        self._linked_sessions = linked_sessions or []
        self._parent_session_id = parent_session_id
        self._existing_session_id = session_id
        self._should_cancel = should_cancel

    def execute(self, mission: ResearchMission) -> AutonomousResearchResult:
        validation = validate_mission(mission)
        if not validation.ok:
            if validation.clarification_message:
                return _clarification_result(mission, validation.clarification_message)
            return _validation_error_result(validation.mission, validation.errors)

        assert validation.mission is not None
        normalized = validation.mission

        if self._existing_session_id:
            research_session = load_session(self._existing_session_id)
            update_session(research_session.id, status="running", error=None)
        else:
            research_session = create_session(
                normalized,
                status="running",
                linked_sessions=self._linked_sessions,
                parent_session_id=self._parent_session_id,
            )

        set_active_session(research_session)

        try:
            prior = _prior_context_for_session(research_session.id)
            prompt = build_mission_prompt(normalized, prior_context=prior or None)

            turn = _run_agent_mission(
                normalized,
                prompt,
                model=self._model,
                api_key=self._api_key,
                max_completion_retries=self._max_completion_retries,
                on_message=self._on_message,
                should_cancel=self._should_cancel,
            )

            if turn.is_error and turn.error == "Cancelled by user":
                update_session(research_session.id, status="cancelled", error=turn.error)
                return AutonomousResearchResult(
                    question=normalized.topic,
                    answer=turn.answer,
                    session_id=research_session.id,
                    num_turns=turn.num_turns,
                    total_cost_usd=turn.total_cost_usd,
                    is_error=True,
                    subtype="cancelled",
                    error=turn.error,
                    mission=normalized,
                )

            missing = verify_deliverables(normalized, answer=turn.answer)
            _persist_turn(
                research_session.id,
                prompt=normalized.topic,
                answer=turn.answer,
                deliverables=normalized.normalized_deliverables(),
                is_error=turn.is_error,
                error=turn.error,
                agent_id=turn.session_id,
                num_turns=turn.num_turns,
                total_cost_usd=turn.total_cost_usd,
            )
            result = _merge_results(
                normalized,
                turn,
                missing=missing,
                research_session_id=research_session.id,
            )
            if not turn.is_error:
                try:
                    publish_session_to_latest(research_session.id)
                except OSError as exc:
                    append_activity(research_session.id, f"[warning] latest publish failed: {exc}")
            return result

        except CursorAgentError as exc:
            update_session(
                research_session.id,
                status="error",
                error=str(exc.message),
            )
            return AutonomousResearchResult(
                question=normalized.topic,
                answer=None,
                session_id=research_session.id,
                num_turns=0,
                total_cost_usd=None,
                is_error=True,
                subtype="error_during_execution",
                error=str(exc.message),
                mission=normalized,
            )
        except OSError as exc:
            update_session(
                research_session.id,
                status="error",
                error=f"Bridge launch failed: {exc}",
            )
            return AutonomousResearchResult(
                question=normalized.topic,
                answer=None,
                session_id=research_session.id,
                num_turns=0,
                total_cost_usd=None,
                is_error=True,
                subtype="error_during_execution",
                error=f"Bridge launch failed: {exc}",
                mission=normalized,
            )
        finally:
            clear_active_session()


def run_autonomous_mission(
    mission: ResearchMission,
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_completion_retries: int = 1,
    on_message: MessageHandler | None = default_activity_handler,
    linked_sessions: list[str] | None = None,
    parent_session_id: str | None = None,
    session_id: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> AutonomousResearchResult:
    """Run one autonomous research mission."""
    agent = AutonomousResearchAgent(
        model=model,
        api_key=api_key,
        max_completion_retries=max_completion_retries,
        on_message=on_message,
        linked_sessions=linked_sessions,
        parent_session_id=parent_session_id,
        session_id=session_id,
        should_cancel=should_cancel,
    )
    return agent.execute(mission)


def run_follow_up_mission(
    session_id: str,
    follow_up_prompt: str,
    deliverables: list[str],
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_completion_retries: int = 1,
    on_message: MessageHandler | None = default_activity_handler,
    should_cancel: Callable[[], bool] | None = None,
) -> AutonomousResearchResult:
    """Continue an existing session with a follow-up research request."""
    session = load_session(session_id)
    mission = ResearchMission(
        topic=session.topic,
        field=session.field,
        objectives=session.objectives or [f"Follow up on: {session.topic}"],
        deliverables=deliverables,
        audience=session.audience,
        depth=session.depth,
    )

    validation = validate_mission(mission)
    if not validation.ok:
        if validation.clarification_message:
            return _clarification_result(mission, validation.clarification_message)
        return _validation_error_result(validation.mission, validation.errors)

    assert validation.mission is not None
    normalized = validation.mission
    set_active_session(session)
    update_session(session_id, status="running", error=None)

    try:
        prior = _prior_context_for_session(session_id)
        turns_ctx = _turns_context(session_id)
        combined_prior = "\n\n".join(part for part in (prior, turns_ctx) if part)
        prompt = build_mission_prompt(
            normalized,
            prior_context=combined_prior or None,
            follow_up_prompt=follow_up_prompt,
        )

        resume_id = session.agent_id
        turn = _run_agent_mission(
            normalized,
            prompt,
            model=model,
            api_key=api_key,
            max_completion_retries=max_completion_retries,
            on_message=on_message,
            resume_agent_id=resume_id,
            should_cancel=should_cancel,
        )

        if turn.is_error and turn.error == "Cancelled by user":
            update_session(session_id, status="cancelled", error=turn.error)
            return AutonomousResearchResult(
                question=normalized.topic,
                answer=turn.answer,
                session_id=session_id,
                num_turns=turn.num_turns,
                total_cost_usd=turn.total_cost_usd,
                is_error=True,
                subtype="cancelled",
                error=turn.error,
                mission=normalized,
            )

        missing = verify_deliverables(normalized, answer=turn.answer)
        _persist_turn(
            session_id,
            prompt=follow_up_prompt,
            answer=turn.answer,
            deliverables=normalized.normalized_deliverables(),
            is_error=turn.is_error,
            error=turn.error,
            agent_id=turn.session_id or session.agent_id,
            num_turns=turn.num_turns,
            total_cost_usd=turn.total_cost_usd,
        )
        return _merge_results(
            normalized,
            turn,
            missing=missing,
            research_session_id=session_id,
        )

    except CursorAgentError as exc:
        update_session(session_id, status="error", error=str(exc.message))
        return AutonomousResearchResult(
            question=normalized.topic,
            answer=None,
            session_id=session_id,
            num_turns=0,
            total_cost_usd=None,
            is_error=True,
            subtype="error_during_execution",
            error=str(exc.message),
            mission=normalized,
        )
    except OSError as exc:
        update_session(session_id, status="error", error=f"Bridge launch failed: {exc}")
        return AutonomousResearchResult(
            question=normalized.topic,
            answer=None,
            session_id=session_id,
            num_turns=0,
            total_cost_usd=None,
            is_error=True,
            subtype="error_during_execution",
            error=f"Bridge launch failed: {exc}",
            mission=normalized,
        )
    finally:
        clear_active_session()
