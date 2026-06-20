"""Reusable Streamlit UI blocks."""

from __future__ import annotations

from typing import Any

import streamlit as st

from deep_research.autonomous_mission import CLARIFICATION_MESSAGE, VALID_DELIVERABLES
from deep_research.session_context import (
    MAX_LINKED_SESSIONS,
    ResearchSession,
    list_session_files,
    list_sessions,
)

DELIVERABLE_LABELS = {
    "answer": "Answer — text synthesis",
    "report": "Report — Markdown + DOCX",
    "mindmap": "Mind map — diagram PNG",
    "slides": "Slides — PowerPoint deck",
    "papers": "Papers — download PDFs",
    "paper_summary": "Paper summaries — PDF digest in Papers/summaries/",
}


def render_header(*, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="dr-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="dr-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_empty_state(message: str) -> None:
    st.markdown(f'<div class="dr-empty">{message}</div>', unsafe_allow_html=True)


def render_activity_log(entries: list[str], *, grouped: bool = True) -> None:
    if not entries:
        st.markdown(
            '<div class="dr-activity-log">Waiting for agent activity…</div>',
            unsafe_allow_html=True,
        )
        return

    if grouped:
        phases: dict[str, list[str]] = {
            "Search": [],
            "Synthesis": [],
            "Artifacts": [],
            "Other": [],
        }
        for entry in entries[-80:]:
            lower = entry.lower()
            if "search" in lower or "tavily" in lower or "literature" in lower:
                phases["Search"].append(entry)
            elif "report" in lower or "diagram" in lower or "slide" in lower or "pdf" in lower:
                phases["Artifacts"].append(entry)
            elif "status" in lower or "assistant" in lower:
                phases["Synthesis"].append(entry)
            else:
                phases["Other"].append(entry)
        lines: list[str] = []
        for phase, items in phases.items():
            if items:
                lines.append(f"## {phase}")
                lines.extend(items)
        text = "\n".join(lines)
    else:
        text = "\n".join(entries[-80:])

    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(f'<div class="dr-activity-log">{escaped}</div>', unsafe_allow_html=True)


def _linkable_sessions() -> list[ResearchSession]:
    return [s for s in list_sessions() if s.status == "completed"]


def _session_option_label(session: ResearchSession) -> str:
    date = session.created_at[:10] if session.created_at else ""
    return f"{session.display_title()[:40]} ({date})"


def render_linked_sessions_picker() -> list[str]:
    """Multiselect for @context session linking (outside form for rerun safety)."""
    prefill: list[str] = st.session_state.get("prefill_linked", [])
    options = _linkable_sessions()
    if not options:
        return prefill[:MAX_LINKED_SESSIONS]

    id_to_label = {s.id: _session_option_label(s) for s in options}
    labels = list(id_to_label.values())
    label_to_id = {v: k for k, v in id_to_label.items()}

    default_labels = [id_to_label[sid] for sid in prefill if sid in id_to_label]
    selected_labels = st.multiselect(
        "Link prior sessions (@context)",
        options=labels,
        default=default_labels,
        max_selections=MAX_LINKED_SESSIONS,
        help="Attach findings from completed sessions as context for this run.",
    )
    return [label_to_id[label] for label in selected_labels]


def render_link_preview(linked_ids: list[str]) -> None:
    if not linked_ids:
        return
    st.caption("**Linked context preview:**")
    for session_id in linked_ids:
        try:
            session = next(s for s in list_sessions() if s.id == session_id)
        except StopIteration:
            continue
        counts = {
            "papers": len(list_session_files(session, "Papers")),
            "reports": len(list_session_files(session, "Reports")),
        }
        st.caption(
            f"- {session.display_title()} · papers={counts['papers']} reports={counts['reports']}"
        )


def render_mission_form(
    *,
    prefill: dict[str, Any] | None = None,
    public_demo: bool = False,
) -> dict[str, Any] | None:
    """Render the new-research form. Returns mission dict on submit, else None."""
    from deep_research.demo_config import allowed_deliverables, pipeline_enabled_in_demo

    data = prefill or {}
    default_topic = data.get("topic", "")
    default_field = data.get("field", "general")
    default_objectives = "\n".join(data.get("objectives", []))
    default_audience = data.get("audience", "informed lay reader")
    default_depth = data.get("depth", "deep")
    permitted = allowed_deliverables() if public_demo else set(VALID_DELIVERABLES)
    default_deliverables = set(data.get("deliverables", ["answer"])) & permitted
    if not default_deliverables:
        default_deliverables = {"answer"} if "answer" in permitted else set(permitted)
    default_scope = data.get("scope", "") or ""
    default_constraints = data.get("constraints", "") or ""
    default_success = "\n".join(data.get("success_criteria", []))
    default_max_retries = int(data.get("max_retries", st.session_state.get("max_retries", 1)))

    linked_ids = render_linked_sessions_picker()
    render_link_preview(linked_ids)

    with st.form("mission_form", clear_on_submit=False):
        topic = st.text_input("Topic *", value=default_topic, placeholder="e.g. CRISPR gene editing in agriculture")
        field = st.text_input("Field", value=default_field, placeholder="e.g. biotechnology")
        objectives = st.text_area(
            "Objectives",
            value=default_objectives,
            placeholder="Leave empty to auto-derive from topic",
            height=100,
        )
        st.markdown("**Deliverables**")
        deliverables: dict[str, bool] = {}
        cols = st.columns(2)
        items = [key for key in VALID_DELIVERABLES if key in permitted]
        if public_demo and len(items) < len(VALID_DELIVERABLES):
            st.caption("Public demo: deliverables limited to reduce API cost.")
        for index, key in enumerate(items):
            label = DELIVERABLE_LABELS.get(key, key)
            with cols[index % 2]:
                deliverables[key] = st.checkbox(
                    label,
                    value=(key in default_deliverables),
                    key=f"del_{key}",
                )

        col_a, col_b = st.columns(2)
        with col_a:
            depth = st.selectbox("Depth", ["deep", "overview"], index=0 if default_depth == "deep" else 1)
        with col_b:
            audience = st.text_input("Audience", value=default_audience)

        max_retries = st.slider(
            "Artifact retry attempts",
            min_value=0,
            max_value=3,
            value=default_max_retries,
            help="How many times to retry if deliverables are missing after the first run.",
        )

        with st.expander("Advanced mission settings", expanded=bool(default_scope or default_constraints or default_success)):
            scope = st.text_area(
                "Scope",
                value=default_scope,
                placeholder="Boundaries of what to include or exclude",
                height=80,
            )
            constraints = st.text_area(
                "Constraints",
                value=default_constraints,
                placeholder="Time, geography, methodology, or source limits",
                height=80,
            )
            success_criteria = st.text_area(
                "Success criteria (one per line)",
                value=default_success,
                placeholder="e.g. At least 5 peer-reviewed sources cited",
                height=80,
            )
            use_pipeline = False
            if pipeline_enabled_in_demo() or not public_demo:
                use_pipeline = st.checkbox(
                    "Multi-agent pipeline",
                    value=bool(data.get("use_pipeline", False)),
                    help="Search → synthesize → artifacts → review as separate phases.",
                )
            save_template_name = st.text_input(
                "Save as template (name)",
                placeholder="my-literature-review",
            )

        submitted = st.form_submit_button("Start Research", type="primary", use_container_width=True)

    if not submitted:
        return None

    selected = [key for key, checked in deliverables.items() if checked]
    if not selected:
        st.warning(CLARIFICATION_MESSAGE)
        return None

    topic_clean = topic.strip()
    if not topic_clean:
        st.error("Topic is required.")
        return None

    objectives_list = [line.strip() for line in objectives.splitlines() if line.strip()]
    if not objectives_list:
        objectives_list = [f"Research and synthesize findings on: {topic_clean}"]

    parent_id = st.session_state.get("prefill_parent")
    st.session_state["max_retries"] = max_retries

    criteria_list = [line.strip() for line in success_criteria.splitlines() if line.strip()]

    mission_payload = {
        "topic": topic_clean,
        "field": field.strip() or "general",
        "objectives": objectives_list,
        "deliverables": selected,
        "audience": audience.strip() or "informed lay reader",
        "depth": depth,
        "linked_sessions": linked_ids,
        "parent_session_id": parent_id,
        "scope": scope.strip() or None,
        "constraints": constraints.strip() or None,
        "success_criteria": criteria_list,
        "max_retries": max_retries,
        "use_pipeline": use_pipeline,
    }

    if save_template_name.strip():
        from deep_research.web.templates import save_user_template

        save_user_template(save_template_name.strip(), mission_payload)
        st.success(f"Template saved: {save_template_name.strip()}")

    return mission_payload


def render_template_picker() -> dict[str, Any] | None:
    """Optional mission template selector above the main form."""
    from deep_research.web.templates import list_template_names, load_template

    names = list_template_names()
    if not names:
        return None

    choice = st.selectbox(
        "Start from template",
        options=["(blank)"] + names,
        index=0,
        help="Prefill the form from a built-in or saved mission template.",
    )
    if choice == "(blank)":
        return None
    template = load_template(choice)
    if template:
        st.caption(f"Template: **{choice}** — enter your topic below.")
    return template


def session_summary_line(session: ResearchSession) -> str:
    title = session.display_title()
    return f"{title[:48]}{'…' if len(title) > 48 else ''}"
