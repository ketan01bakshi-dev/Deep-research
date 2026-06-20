"""Streamlit UI for public demo gate and footer."""

from __future__ import annotations

import streamlit as st

from deep_research.demo_config import (
    demo_missions_remaining,
    demo_password,
    is_public_demo,
    max_demo_missions_per_day,
)


def render_demo_gate() -> bool:
    """
    When PUBLIC_DEMO is enabled, require DEMO_PASSWORD before using the app.
    Returns True when the user may proceed.
    """
    if not is_public_demo():
        return True

    expected = demo_password()
    if not expected:
        st.warning("Public demo mode is on but DEMO_PASSWORD is not set.")
        return True

    if st.session_state.get("demo_authenticated"):
        return True

    st.markdown("### Deep Research — Public Demo")
    st.caption(
        f"Limited to {max_demo_missions_per_day()} missions per day. "
        "See [Legal & Privacy](docs/LEGAL.md) before submitting sensitive topics."
    )
    entered = st.text_input("Demo password", type="password", key="demo_password_input")
    if st.button("Enter demo", type="primary"):
        if entered == expected:
            st.session_state.demo_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


def render_demo_banner() -> None:
    if not is_public_demo():
        return
    remaining = demo_missions_remaining()
    limit = max_demo_missions_per_day()
    if remaining <= 0:
        st.error(
            f"Daily demo limit reached ({limit} missions). "
            "Clone the repo and run locally with your own API keys."
        )
    else:
        st.info(f"Public demo — {remaining} of {limit} missions remaining today.")


def render_legal_footer() -> None:
    st.divider()
    st.caption(
        "AI outputs may be inaccurate — verify before use. "
        "[Legal & Privacy](docs/LEGAL.md) · "
        "[Security](SECURITY.md) · "
        "Built with Cursor SDK + Tavily."
    )
