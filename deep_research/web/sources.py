"""Verified sources panel for session Answer tab."""

from __future__ import annotations

import json

import streamlit as st
from agent_core.io import load_json, save_json

from deep_research.session_context import ResearchSession, clear_active_session, set_active_session
from deep_research.tools import source_verify


def render_sources_panel(session: ResearchSession) -> None:
    """Show sources.json with verification status and re-verify controls."""
    path = session.root / "sources.json"
    if not path.exists():
        st.caption("No sources.json for this session yet.")
        return

    data = load_json(path, default={})
    sources = list(data.get("sources") or [])
    if not sources:
        return

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### Sources ({len(sources)})")
    with col2:
        filter_mode = st.selectbox(
            "Filter",
            ["all", "ok", "dead", "unverified"],
            key=f"sources_filter_{session.id}",
            label_visibility="collapsed",
        )
    with col3:
        if st.button("Re-verify", key=f"verify_sources_{session.id}"):
            set_active_session(session)
            try:
                payload = json.loads(
                    source_verify.verify_sources(
                        {"urls": [s.get("url") for s in sources if s.get("url")]},
                        None,
                    )
                )
            finally:
                clear_active_session()
            save_json(path, {"sources": payload.get("sources") or [], "count": payload.get("verified_count", 0)})
            st.success(f"Verified {payload.get('verified_count', 0)} source(s).")
            st.rerun()

    for item in sources:
        url = item.get("url") or ""
        title = item.get("title") or url
        ok = item.get("ok")
        if ok is True:
            status = "ok"
        elif ok is False:
            status = "dead"
        else:
            status = "unverified"
        if filter_mode != "all" and status != filter_mode:
            continue
        st.markdown(f"- **{title}** — `{status}`")
        if url:
            st.markdown(f"[{url}]({url})")
        snippet = item.get("snippet")
        if snippet:
            st.caption(snippet[:200])
