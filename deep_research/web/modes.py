"""Streamlit UI for Phase 1 (quick) and Phase 2 (chat) modes."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from deep_research.autonomous_mission import ResearchMission
from deep_research.session_context import create_session, update_session


def _chat_history_path() -> Path:
    return Path(st.session_state.get("chat_history_file", "profile/.chat_history.json"))


def load_persisted_chat_history() -> list[dict]:
    path = _chat_history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_persisted_chat_history(history: list[dict]) -> None:
    path = _chat_history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history[-50:], indent=2), encoding="utf-8")


def render_quick_query_mode() -> dict | None:
    """Return payload to start a background quick query run."""
    st.markdown("### Quick research (Phase 1)")
    st.caption("One-shot query — optional save to session after completion.")
    prompt = st.text_area("Research question", height=120, key="quick_prompt")
    save_session = st.checkbox("Save result as session", value=False, key="quick_save_session")
    if st.button("Run quick research", type="primary", key="quick_run"):
        if not prompt.strip():
            st.error("Enter a question.")
            return None
        return {"prompt": prompt.strip(), "save_session": save_session}
    return None


def render_chat_mode() -> dict | None:
    """Return payload to start a background chat turn."""
    st.markdown("### Guided chat (Phase 2)")
    st.caption("Multi-turn conversation with agent memory.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_persisted_chat_history()
    if "chat_agent_id" not in st.session_state:
        st.session_state.chat_agent_id = None

    for entry in st.session_state.chat_history:
        st.markdown(f"**You:** {entry['prompt']}")
        if entry.get("answer"):
            st.markdown(entry["answer"])
        elif entry.get("error"):
            st.error(entry["error"])
        st.divider()

    prompt = st.text_area("Your message", height=100, key="chat_prompt")
    col1, col2, col3 = st.columns(3)
    with col1:
        send = st.button("Send", type="primary", key="chat_send")
    with col2:
        if st.button("New chat", key="chat_reset"):
            st.session_state.chat_history = []
            st.session_state.chat_agent_id = None
            save_persisted_chat_history([])
            st.rerun()
    with col3:
        promote = st.button("Promote to full mission", key="chat_promote")

    if promote and st.session_state.chat_history:
        last = st.session_state.chat_history[-1]
        st.session_state.view_mode = "new"
        st.session_state.prefill_mission = {
            "topic": last.get("prompt", "Follow-up research")[:120],
            "field": "general",
            "objectives": ["Continue guided chat research with full deliverables"],
            "deliverables": ["answer", "report"],
        }
        st.rerun()

    if not send:
        return None
    if not prompt.strip():
        st.error("Enter a message.")
        return None
    return {
        "prompt": prompt.strip(),
        "agent_id": st.session_state.chat_agent_id,
    }


def create_quick_query_session(prompt: str, answer: str) -> str:
    mission = ResearchMission(
        topic=prompt[:120],
        field="general",
        objectives=[f"Quick query: {prompt[:200]}"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="completed")
    update_session(session.id, answer=answer, title=prompt[:80])
    return session.id
