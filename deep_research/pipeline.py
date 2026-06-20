"""Multi-agent sequential research pipeline (search → synthesize → artifacts → review)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cursor_sdk import Agent, CursorAgentError

from cursor_agent_core.bridge.client import cursor_client
from deep_research.autonomous_mission import (
    ResearchMission,
    build_mission_prompt,
    collect_artifacts,
    validate_mission,
    verify_deliverables,
)
from deep_research.autonomous_prompts import system_prompt_for_field
from deep_research.autonomous import (
    _merge_results,
    _persist_turn,
    _run_turn_cancellable,
)
from deep_research.cursor_options import build_agent_options, project_cwd
from deep_research.display import default_activity_handler
from deep_research.session_context import (
    append_activity,
    clear_active_session,
    create_session,
    get_session_context_bundle,
    load_session,
    set_active_session,
    update_session,
)
from deep_research.types import AutonomousResearchResult


def _cancelled_turn(topic: str) -> Any:
    from deep_research.cursor_adapter import error_result

    return error_result(topic, error="Cancelled by user")


def _phase_prompt(mission: ResearchMission, phase: str, *, prior: str = "") -> str:
    base = build_mission_prompt(mission, prior_context=prior or None)
    if phase == "search":
        return (
            base
            + "\n\n## Phase: Search only\n"
            "Run 3-4 Tavily searches. Call verify_sources. "
            "Do NOT create report/mindmap/slides yet. Output a source brief in your answer."
        )
    if phase == "synthesize":
        return (
            base
            + "\n\n## Phase: Synthesis\n"
            "Using prior search brief, write the full text answer. No artifact files yet."
        )
    if phase == "artifacts":
        return (
            base
            + "\n\n## Phase: Artifacts\n"
            "Create ONLY missing deliverable files (report, mindmap, slides, papers). "
            "Do not repeat the full answer."
        )
    if phase == "review":
        return (
            base
            + "\n\n## Phase: Review\n"
            "Check deliverables, call complete_mission with assumptions and artifact paths."
        )
    return base


def run_pipeline_mission(
    mission: ResearchMission,
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_completion_retries: int = 1,
    on_message: Any = default_activity_handler,
    linked_sessions: list[str] | None = None,
    parent_session_id: str | None = None,
    session_id: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> AutonomousResearchResult:
    """Run mission as four sequential focused agent phases in one session."""
    validation = validate_mission(mission)
    if not validation.ok:
        from deep_research.autonomous import _clarification_result, _validation_error_result

        if validation.clarification_message:
            return _clarification_result(mission, validation.clarification_message)
        return _validation_error_result(validation.mission, validation.errors)

    assert validation.mission is not None
    normalized = validation.mission

    if session_id:
        research_session = load_session(session_id)
        update_session(research_session.id, status="running", error=None)
    else:
        research_session = create_session(
            normalized,
            status="running",
            linked_sessions=linked_sessions,
            parent_session_id=parent_session_id,
        )

    set_active_session(research_session)
    prior_ctx = ""
    if research_session.linked_sessions:
        prior_ctx = get_session_context_bundle(research_session.linked_sessions)

    options = build_agent_options(model=model, api_key=api_key)
    system = system_prompt_for_field(normalized.field)
    last_turn: Any = None

    try:
        with cursor_client(workspace=project_cwd()) as client:
            with Agent.create(options, client=client) as agent:
                context = prior_ctx
                for phase in ("search", "synthesize", "artifacts", "review"):
                    if should_cancel and should_cancel():
                        last_turn = _cancelled_turn(normalized.topic)
                        break
                    prompt = _phase_prompt(normalized, phase, prior=context)
                    last_turn = _run_turn_cancellable(
                        agent,
                        prompt,
                        on_message=on_message,
                        prefix_system=system,
                        should_cancel=should_cancel,
                    )
                    if last_turn.is_error:
                        if last_turn.error == "Cancelled by user":
                            update_session(research_session.id, status="cancelled", error=last_turn.error)
                            return AutonomousResearchResult(
                                question=normalized.topic,
                                answer=last_turn.answer,
                                session_id=research_session.id,
                                num_turns=last_turn.num_turns,
                                total_cost_usd=last_turn.total_cost_usd,
                                is_error=True,
                                subtype="cancelled",
                                error=last_turn.error,
                                mission=normalized,
                            )
                        break
                    if last_turn.answer:
                        context = (context + "\n\n" + last_turn.answer)[-8000:]

                retries = 0
                while retries < max_completion_retries and last_turn and not last_turn.is_error:
                    if should_cancel and should_cancel():
                        last_turn = _cancelled_turn(normalized.topic)
                        break
                    missing = verify_deliverables(normalized, answer=last_turn.answer)
                    if not missing:
                        break
                    retries += 1
                    cont = (
                        f"Pipeline continuation — missing: {', '.join(missing)}. "
                        "Create missing items and call complete_mission."
                    )
                    last_turn = _run_turn_cancellable(
                        agent,
                        cont,
                        on_message=on_message,
                        prefix_system=None,
                        should_cancel=should_cancel,
                    )

        if last_turn is None:
            raise RuntimeError("Pipeline produced no agent turn")

        if last_turn.is_error and last_turn.error == "Cancelled by user":
            update_session(research_session.id, status="cancelled", error=last_turn.error)
            return AutonomousResearchResult(
                question=normalized.topic,
                answer=last_turn.answer,
                session_id=research_session.id,
                num_turns=last_turn.num_turns,
                total_cost_usd=last_turn.total_cost_usd,
                is_error=True,
                subtype="cancelled",
                error=last_turn.error,
                mission=normalized,
            )

        missing = verify_deliverables(normalized, answer=last_turn.answer)
        _persist_turn(
            research_session.id,
            prompt=normalized.topic,
            answer=last_turn.answer,
            deliverables=normalized.normalized_deliverables(),
            is_error=last_turn.is_error,
            error=last_turn.error,
            agent_id=last_turn.session_id,
            num_turns=last_turn.num_turns,
            total_cost_usd=last_turn.total_cost_usd,
        )
        from deep_research.session_context import publish_session_to_latest

        if not last_turn.is_error:
            try:
                publish_session_to_latest(research_session.id)
            except OSError as exc:
                append_activity(research_session.id, f"[warning] latest publish failed: {exc}")
        return _merge_results(
            normalized,
            last_turn,
            missing=missing,
            research_session_id=research_session.id,
        )

    except (CursorAgentError, OSError) as exc:
        error = str(getattr(exc, "message", exc))
        update_session(research_session.id, status="error", error=error)
        return AutonomousResearchResult(
            question=normalized.topic,
            answer=None,
            session_id=research_session.id,
            num_turns=0,
            total_cost_usd=None,
            is_error=True,
            subtype="error_during_execution",
            error=error,
            mission=normalized,
        )
    finally:
        clear_active_session()
