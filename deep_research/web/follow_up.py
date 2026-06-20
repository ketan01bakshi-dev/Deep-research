"""Follow-up research UI for multi-turn sessions."""

from __future__ import annotations

import streamlit as st

from deep_research.autonomous_mission import VALID_DELIVERABLES
from deep_research.session_context import ResearchSession, load_turns
from deep_research.web.components import DELIVERABLE_LABELS


def render_turn_timeline(session: ResearchSession) -> None:
    turns = load_turns(session.id)
    if not turns:
        if session.answer:
            st.markdown("### Turn 1")
            st.markdown(session.answer)
        return

    for index, turn in enumerate(turns, start=1):
        st.markdown(f"### Turn {index}")
        st.caption(f"Request: {turn.prompt}")
        if turn.is_error and turn.error:
            st.error(turn.error)
        elif turn.answer:
            st.markdown(turn.answer)
        else:
            st.info("No answer for this turn.")
        if turn.deliverables:
            st.caption("Deliverables: " + ", ".join(turn.deliverables))
        st.divider()


def render_follow_up_form(session: ResearchSession) -> dict | None:
    """Render follow-up input. Returns payload dict on submit."""
    if session.status == "running":
        st.info("Research is in progress for this session.")
        return None

    st.markdown("### Follow-up")
    with st.form(f"follow_up_{session.id}"):
        prompt = st.text_area(
            "Continue this research thread",
            placeholder="e.g. Dig deeper into the regulatory landscape in the EU",
            height=100,
        )
        st.markdown("**Deliverables for this follow-up**")
        deliverables: dict[str, bool] = {}
        cols = st.columns(2)
        for index, key in enumerate(VALID_DELIVERABLES):
            with cols[index % 2]:
                deliverables[key] = st.checkbox(
                    DELIVERABLE_LABELS.get(key, key),
                    value=(key == "answer"),
                    key=f"fu_{session.id}_{key}",
                )
        max_retries = st.slider(
            "Completion retries",
            min_value=0,
            max_value=3,
            value=1,
            key=f"fu_{session.id}_max_retries",
            help="Retry missing deliverables before finishing this follow-up.",
        )

        submitted = st.form_submit_button("Continue research", type="primary")

    if not submitted:
        return None

    selected = [k for k, v in deliverables.items() if v]
    if not selected:
        st.warning("Select at least one deliverable for the follow-up.")
        return None

    prompt_clean = prompt.strip()
    if not prompt_clean:
        st.error("Follow-up prompt is required.")
        return None

    return {"prompt": prompt_clean, "deliverables": selected, "max_retries": max_retries}
