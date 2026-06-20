"""Shared message display and result formatting."""

from __future__ import annotations

from typing import Any

from deep_research.session_context import append_activity, get_active_session
from deep_research.types import AutonomousResearchResult, ResearchResult


def default_activity_handler(message: Any) -> None:
    """Log tool/status activity to the active session (CLI parity with Streamlit)."""
    session = get_active_session()
    if session is None:
        return

    msg_type = getattr(message, "type", None)
    if msg_type == "tool_call":
        name = getattr(message, "name", "tool")
        status = getattr(message, "status", "")
        if status == "running":
            append_activity(session.id, f"[tool] {name}")
        elif status == "completed":
            append_activity(session.id, f"[tool done] {name}")
    elif msg_type == "status":
        detail = getattr(message, "message", "") or getattr(message, "status", "")
        if detail:
            append_activity(session.id, f"[status] {detail}")


def format_result_summary(
    result: ResearchResult,
    *,
    session_label: str = "Agent",
) -> str:
    """Human-readable footer for a completed research run."""
    lines = [
        "",
        "=" * 72,
        f"Turns: {result.num_turns}",
    ]
    if result.total_cost_usd is not None:
        lines.append(f"Estimated cost: ${result.total_cost_usd:.4f}")
    if result.session_id:
        lines.append(f"{session_label} ID: {result.session_id}")
    if result.is_error:
        detail = result.error or result.subtype
        lines.append(f"Status: error ({detail})")
    else:
        lines.append(f"Status: {result.subtype or 'complete'}")
    lines.append("=" * 72)
    return "\n".join(lines)


def format_autonomous_summary(result: AutonomousResearchResult) -> str:
    """Footer for autonomous mission runs including artifact manifest."""
    lines = [format_result_summary(result)]

    if result.clarification_needed:
        lines.insert(-1, "Action: specify deliverables and re-run.")
        return "\n".join(lines)

    if result.mission is not None:
        deliverables = result.mission.normalized_deliverables()
        lines.insert(-1, f"Deliverables requested: {', '.join(deliverables)}")

    if result.assumptions:
        lines.insert(-1, "Assumptions:")
        for item in result.assumptions:
            lines.insert(-1, f"  - {item}")

    if result.artifacts:
        lines.insert(-1, "Artifacts:")
        for path in result.artifacts:
            lines.insert(-1, f"  - {path}")

    if result.missing_deliverables:
        lines.insert(
            -1,
            f"Missing deliverables: {', '.join(result.missing_deliverables)}",
        )

    return "\n".join(lines)
