"""Completion manifest viewer for session detail."""

from __future__ import annotations

import streamlit as st

from deep_research.session_context import ResearchSession, load_completion


def render_completion_tab(session: ResearchSession) -> None:
    """Show completion.json summary, assumptions, and artifacts."""
    completion = load_completion(session)
    if not completion:
        st.info("No completion manifest yet. The agent writes this when it calls complete_mission.")
        return

    if completion.get("summary"):
        st.markdown("### Summary")
        st.markdown(completion["summary"])

    assumptions = completion.get("assumptions") or []
    if assumptions:
        st.markdown("### Assumptions")
        for item in assumptions:
            st.markdown(f"- {item}")

    artifacts = completion.get("artifacts") or []
    if artifacts:
        st.markdown("### Artifacts logged")
        for path in artifacts:
            st.markdown(f"- `{path}`")

    met = completion.get("success_criteria_met")
    if met is not None:
        label = "Yes" if met else "No"
        st.markdown(f"**Success criteria met:** {label}")

    if completion.get("completed_at"):
        st.caption(f"Completed at: {completion['completed_at']}")


def render_session_warnings(
    *,
    missing_deliverables: list[str] | None,
    assumptions: list[str] | None,
) -> None:
    """Show missing deliverable warning and assumptions banner on session detail."""
    if missing_deliverables:
        st.warning(
            "Some requested deliverables were not produced: "
            + ", ".join(missing_deliverables)
            + ". Use **Retry** to run again."
        )
    if assumptions:
        with st.expander("Agent assumptions", expanded=False):
            for item in assumptions:
                st.markdown(f"- {item}")
