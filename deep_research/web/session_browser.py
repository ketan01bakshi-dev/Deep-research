"""Left-panel session browser for past research queries."""

from __future__ import annotations

import streamlit as st

from deep_research.session_context import (
    ResearchSession,
    delete_failed_sessions,
    delete_session,
    list_session_files,
    list_sessions,
    list_unreadable_session_meta,
    load_session,
    update_session,
)
from deep_research.web.components import session_summary_line
from deep_research.web.session_browser_keys import session_row_widget_keys
from deep_research.web.styles import status_badge


@st.cache_data(ttl=15)
def _artifact_counts_cached(session_id: str, status: str, created_at: str) -> dict[str, int]:
    _ = (status, created_at)
    session = load_session(session_id)
    return {
        "Papers": len(list_session_files(session, "Papers")),
        "Reports": len(list_session_files(session, "Reports")),
        "Diagrams": len(list_session_files(session, "Diagrams")),
        "Slides": len(list_session_files(session, "Slides")),
    }


def _artifact_counts(session: ResearchSession) -> dict[str, int]:
    return _artifact_counts_cached(session.id, session.status, session.created_at)


def _confirm_delete_dialog(session_id: str, title: str) -> None:
    @st.dialog(f"Delete session?")
    def _dialog() -> None:
        st.warning(f"Permanently delete **{title}** and all artifacts?")
        confirm = st.checkbox("I understand this cannot be undone")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Delete", type="primary", disabled=not confirm):
                delete_session(session_id)
                if st.session_state.get("selected_session_id") == session_id:
                    st.session_state.selected_session_id = None
                    st.session_state.view_mode = "new"
                st.session_state.pop("delete_target", None)
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.pop("delete_target", None)
                st.rerun()

    _dialog()


def _confirm_bulk_delete_dialog(session_ids: list[str]) -> None:
    @st.dialog("Delete selected sessions?")
    def _dialog() -> None:
        st.warning(f"Permanently delete {len(session_ids)} selected session(s) and all artifacts?")
        confirm = st.checkbox("I understand this cannot be undone", key="bulk_delete_confirm_check")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Delete selected", type="primary", disabled=not confirm):
                for sid in session_ids:
                    try:
                        delete_session(sid)
                    except FileNotFoundError:
                        continue
                st.session_state.bulk_selected = []
                st.session_state.selected_session_id = None
                st.session_state.view_mode = "new"
                st.session_state.pop("bulk_delete_target", None)
                st.rerun()
        with col2:
            if st.button("Cancel", key="cancel_bulk_delete"):
                st.session_state.pop("bulk_delete_target", None)
                st.rerun()

    _dialog()


def render_session_browser() -> str | None:
    """Render sidebar session list. Returns selected session_id or None."""
    st.sidebar.markdown("### Deep Research")
    ui_mode = st.sidebar.radio(
        "Mode",
        ["Full mission", "Quick query", "Guided chat"],
        index=["Full mission", "Quick query", "Guided chat"].index(
            st.session_state.get("ui_mode", "Full mission")
        ),
        key="ui_mode_radio",
    )
    st.session_state["ui_mode"] = ui_mode

    if st.sidebar.button("+ New query", use_container_width=True):
        st.session_state.selected_session_id = None
        st.session_state.view_mode = "new"
        st.session_state.pop("prefill_linked", None)
        st.session_state.pop("prefill_parent", None)
        st.session_state.pop("prefill_mission", None)
        st.session_state.pop("last_result", None)
        st.session_state.bulk_selected = []
        st.rerun()

    st.sidebar.markdown("---")

    search = st.sidebar.text_input("Search sessions", key="session_search", placeholder="Topic, field, tag…")
    status_filter = st.sidebar.selectbox(
        "Status",
        ["all", "completed", "error", "running", "pending", "cancelled"],
        index=0,
        key="session_status_filter",
    )
    field_filter = st.sidebar.selectbox(
        "Field",
        ["all", "general", "health", "science", "technology", "policy", "business"],
        index=0,
        key="session_field_filter",
    )
    deliverable_filter = st.sidebar.selectbox(
        "Deliverable",
        ["all", "answer", "report", "mindmap", "slides", "papers", "paper_summary"],
        index=0,
        key="session_deliverable_filter",
    )
    tag_filter = st.sidebar.text_input("Tag filter", key="session_tag_filter", placeholder="e.g. diabetes")

    sessions = list_sessions(
        search=search,
        status_filter=status_filter,
        field_filter=field_filter,
        deliverable_filter=deliverable_filter,
        tag_filter=tag_filter,
    )
    unreadable = list_unreadable_session_meta()
    if unreadable:
        st.sidebar.warning(f"{len(unreadable)} session metadata file(s) could not be read.")

    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.button("Clear failed", use_container_width=True, help="Delete all error sessions"):
            count = delete_failed_sessions()
            current = st.session_state.get("selected_session_id")
            if current and current not in {s.id for s in list_sessions()}:
                st.session_state.selected_session_id = None
                st.session_state.view_mode = "new"
            st.sidebar.success(f"Deleted {count} failed session(s).")
            st.rerun()
    with col_b:
        bulk_mode = st.toggle("Bulk delete", key="bulk_delete_mode")

    st.sidebar.markdown("**Past sessions**")

    if not sessions:
        st.sidebar.caption("No matching sessions.")
        return st.session_state.get("selected_session_id")

    selected_id = st.session_state.get("selected_session_id")
    bulk_selected: list[str] = st.session_state.get("bulk_selected", [])

    if bulk_mode and bulk_selected:
        if st.sidebar.button(f"Delete {len(bulk_selected)} selected", type="primary"):
            st.session_state.bulk_delete_target = list(bulk_selected)
            st.rerun()

    if st.session_state.get("bulk_delete_target"):
        _confirm_bulk_delete_dialog(list(st.session_state.bulk_delete_target))

    for row_idx, session in enumerate(sessions):
        counts = _artifact_counts(session)
        label = session_summary_line(session)
        badge = status_badge(session.status)
        pin_prefix = "[pinned] " if session.pinned else ""
        is_active = session.id == selected_id

        container_class = "dr-session-item dr-session-active" if is_active else "dr-session-item"
        st.sidebar.markdown(
            f'<div class="{container_class}">{badge}<br><strong>{pin_prefix}{label}</strong></div>',
            unsafe_allow_html=True,
        )
        detail_parts = [
            f"Papers ({counts['Papers']})" if counts["Papers"] else None,
            f"Reports ({counts['Reports']})" if counts["Reports"] else None,
            f"Mind maps ({counts['Diagrams']})" if counts["Diagrams"] else None,
            f"Slides ({counts['Slides']})" if counts["Slides"] else None,
        ]
        detail = " · ".join(p for p in detail_parts if p)
        if detail:
            st.sidebar.caption(detail)

        btn_cols = st.sidebar.columns([2, 1, 1] if not bulk_mode else [1, 1, 1, 1])
        row_keys = session_row_widget_keys(session.id, row_idx)
        col_idx = 0
        if bulk_mode:
            checked = session.id in bulk_selected
            if btn_cols[col_idx].checkbox(
                "Sel",
                value=checked,
                key=row_keys["bulk"],
                label_visibility="collapsed",
            ):
                if session.id not in bulk_selected:
                    bulk_selected.append(session.id)
            else:
                if session.id in bulk_selected:
                    bulk_selected.remove(session.id)
            col_idx += 1
        st.session_state.bulk_selected = bulk_selected

        if btn_cols[col_idx].button(
            "Open",
            key=row_keys["open"],
            use_container_width=True,
        ):
            st.session_state.selected_session_id = session.id
            st.session_state.view_mode = "session"
            st.rerun()
        col_idx += 1

        pin_label = "Unpin" if session.pinned else "Pin"
        if btn_cols[col_idx].button(
            pin_label,
            key=row_keys["pin"],
            use_container_width=True,
        ):
            update_session(session.id, pinned=not session.pinned)
            st.rerun()
        col_idx += 1

        if btn_cols[col_idx].button(
            "Del",
            key=row_keys["del"],
            use_container_width=True,
        ):
            st.session_state.delete_target = session.id
            st.session_state.delete_target_title = session.display_title()

    if st.session_state.get("delete_target"):
        _confirm_delete_dialog(
            st.session_state.delete_target,
            st.session_state.get("delete_target_title", "session"),
        )

    _render_compare_sessions(sessions)

    return selected_id


def _render_compare_sessions(sessions: list[ResearchSession]) -> None:
    completed = [s for s in sessions if s.status == "completed"]
    if len(completed) < 2:
        return
    with st.sidebar.expander("Compare sessions"):
        options = {s.id: session_summary_line(s) for s in completed[:20]}
        picked = st.multiselect(
            "Pick two sessions",
            options=list(options.keys()),
            format_func=lambda sid: options[sid],
            max_selections=2,
            key="compare_sessions",
        )
        if len(picked) == 2:
            a, b = (load_session_by_id(picked[0], completed), load_session_by_id(picked[1], completed))
            if a and b:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{a.display_title()}**")
                    st.caption(f"Field: {a.field} · {a.created_at[:10]}")
                    st.caption("Deliverables: " + ", ".join(a.deliverables))
                    if a.answer:
                        st.markdown(a.answer[:1200] + ("…" if len(a.answer or "") > 1200 else ""))
                with col2:
                    st.markdown(f"**{b.display_title()}**")
                    st.caption(f"Field: {b.field} · {b.created_at[:10]}")
                    st.caption("Deliverables: " + ", ".join(b.deliverables))
                    if b.answer:
                        st.markdown(b.answer[:1200] + ("…" if len(b.answer or "") > 1200 else ""))


def load_session_by_id(session_id: str, pool: list[ResearchSession]) -> ResearchSession | None:
    return next((s for s in pool if s.id == session_id), None)
