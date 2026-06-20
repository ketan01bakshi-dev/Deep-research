"""Streamlit entry point for Deep Research."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import streamlit as st
from agent_core import load_agent_env

from deep_research.autonomous import run_autonomous_mission, run_follow_up_mission
from deep_research.pipeline import run_pipeline_mission
from deep_research.autonomous_mission import mission_from_dict
from deep_research.session_context import (
    append_activity,
    find_referencing_sessions,
    load_activity,
    load_session,
    mark_stale_running_sessions,
    mission_dict_from_session,
    update_session,
)
from deep_research.web.completion import render_completion_tab, render_session_warnings
from deep_research.web.components import (
    render_activity_log,
    render_header,
    render_mission_form,
    render_template_picker,
)
from deep_research.web.follow_up import render_follow_up_form, render_turn_timeline
from deep_research.web.pdf_viewer import (
    render_mindmap_tab,
    render_papers_tab,
    render_report_tab,
    render_slides_tab,
)
from deep_research.web.modes import (
    create_quick_query_session,
    render_chat_mode,
    render_quick_query_mode,
    save_persisted_chat_history,
)
from deep_research.web.sources import render_sources_panel
from deep_research.web.export import export_session_zip_enhanced
from deep_research.web.background_runs import (
    BackgroundRun,
    TERMINAL_STATUSES,
    create_background_run,
    forget_background_run,
    get_background_run,
)
from deep_research.web.session_browser import render_session_browser
from deep_research.web.styles import apply_page_config, inject_styles, status_badge

PROJECT_ROOT = Path(__file__).resolve().parent
load_agent_env(PROJECT_ROOT)

from deep_research.demo_config import (  # noqa: E402
    apply_streamlit_secrets,
    can_start_demo_mission,
    is_public_demo,
    record_demo_mission_start,
)
from deep_research.demo_limits import purge_expired_demo_sessions  # noqa: E402
from deep_research.web.demo_gate import (  # noqa: E402
    render_demo_banner,
    render_demo_gate,
    render_legal_footer,
)

apply_streamlit_secrets()


def _open_session(session_id: str) -> None:
    st.session_state.selected_session_id = session_id
    st.session_state.view_mode = "session"
    try:
        st.query_params["session"] = session_id
    except Exception:
        pass
    st.rerun()


def _sync_query_params() -> None:
    try:
        qp_session = st.query_params.get("session")
    except Exception:
        return
    if qp_session and qp_session != st.session_state.get("selected_session_id"):
        st.session_state.selected_session_id = qp_session
        st.session_state.view_mode = "session"


def _quick_query_target(payload: dict[str, Any]):
    def _target(run_state: BackgroundRun):
        from deep_research.agent import run_research

        result = run_research(payload["prompt"])
        if payload.get("save_session") and result.answer and not result.is_error:
            session_id = create_quick_query_session(payload["prompt"], result.answer)
            result.session_id = session_id  # type: ignore[attr-defined]
        return result

    return _target


def _chat_target(payload: dict[str, Any]):
    def _target(run_state: BackgroundRun):
        from deep_research.conversation import ConversationalResearchAgent, resume_research

        if payload.get("agent_id"):
            result = resume_research(payload["agent_id"], payload["prompt"])
            agent_id = payload["agent_id"]
        else:
            with ConversationalResearchAgent() as agent:
                result = agent.ask(payload["prompt"])
                agent_id = agent.session_id
        history = st.session_state.get("chat_history", [])
        history.append(
            {"prompt": payload["prompt"], "answer": result.answer, "error": result.error}
        )
        st.session_state.chat_history = history
        st.session_state.chat_agent_id = agent_id
        save_persisted_chat_history(history)
        return result

    return _target


def _check_demo_mission_limit() -> bool:
    if not is_public_demo():
        return True
    if not can_start_demo_mission():
        st.error(
            "Daily demo mission limit reached. "
            "Clone the GitHub repo and run locally with your own API keys."
        )
        return False
    record_demo_mission_start()
    return True


def _start_quick_query(payload: dict[str, Any]) -> None:
    if not _render_env_banner():
        return
    if not _check_demo_mission_limit():
        return
    st.session_state.running = True
    run = create_background_run("quick_query", "Quick research...", _quick_query_target(payload))
    st.session_state.active_run_id = run.id
    st.rerun()


def _start_chat(payload: dict[str, Any]) -> None:
    if not _render_env_banner():
        return
    if not _check_demo_mission_limit():
        return
    st.session_state.running = True
    run = create_background_run("chat", "Guided chat...", _chat_target(payload))
    st.session_state.active_run_id = run.id
    st.rerun()


def _missing_env_keys() -> tuple[list[str], list[str]]:
    """Return (required_missing, optional_missing) API key names."""
    required: list[str] = []
    optional: list[str] = []
    if not os.environ.get("CURSOR_API_KEY", "").strip():
        required.append("CURSOR_API_KEY")
    if not os.environ.get("TAVILY_API_KEY", "").strip():
        optional.append("TAVILY_API_KEY")
    return required, optional


def _render_env_banner() -> bool:
    required, optional = _missing_env_keys()
    if required:
        st.error(
            "Missing required API keys: "
            + ", ".join(required)
            + ". Copy `.env.example` to `.env` in the project root and add your keys, "
            "then restart the app."
        )
        return False
    if optional:
        st.warning(
            "Optional key missing: "
            + ", ".join(optional)
            + ". Web search and PDF download tools will be unavailable until you set it in `.env`."
        )
    return True


def _init_state() -> None:
    defaults = {
        "selected_session_id": None,
        "view_mode": "new",
        "activity": [],
        "streamed_answer": "",
        "last_result": None,
        "running": False,
        "prefill_linked": [],
        "prefill_parent": None,
        "prefill_mission": None,
        "bulk_selected": [],
        "active_run_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _activity_handler_factory(
    log: list[str],
    *,
    session_id: str | None,
    stream_placeholder: Any | None = None,
    run_state: BackgroundRun | None = None,
):
    buffer: list[str] = []

    def record_activity(entry: str) -> None:
        log.append(entry)
        if run_state is not None:
            run_state.add_activity(entry)
        target_session_id = session_id or (run_state.session_id if run_state else None)
        if target_session_id:
            append_activity(target_session_id, entry)

    def handler(message: Any) -> None:
        if run_state is not None and run_state.should_cancel():
            return

        msg_type = getattr(message, "type", None)
        if msg_type == "tool_call":
            name = getattr(message, "name", "tool")
            status = getattr(message, "status", "")
            detail = getattr(message, "input", "") or ""
            if status == "running":
                record_activity(f"[tool] {name}")
            elif status == "completed":
                record_activity(f"[tool done] {name}")
        elif msg_type == "assistant":
            content = getattr(getattr(message, "message", None), "content", None) or []
            for block in content:
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "")
                    if text:
                        buffer.append(text)
                        combined = "".join(buffer)
                        if run_state is not None:
                            run_state.set_streamed_answer(combined)
                        else:
                            st.session_state.streamed_answer = combined
                        if stream_placeholder is not None:
                            stream_placeholder.markdown(combined)
        elif msg_type == "status":
            detail = getattr(message, "message", "") or getattr(message, "status", "")
            if detail:
                record_activity(f"[status] {detail}")
        elif msg_type == "result":
            cost = getattr(message, "total_cost_usd", None)
            if cost is not None:
                if run_state is not None:
                    run_state.set_live_cost(cost)
                else:
                    st.session_state["live_cost_usd"] = cost

    return handler


def _mission_target(
    mission_data: dict[str, Any],
    *,
    retry_session_id: str | None = None,
):
    def _target(run_state: BackgroundRun):
        mission = mission_from_dict(mission_data)
        linked = mission_data.get("linked_sessions") or []
        parent = mission_data.get("parent_session_id")
        max_retries = int(mission_data.get("max_retries", 1))
        run_state.session_id = retry_session_id
        handler = _activity_handler_factory(
            [],
            session_id=retry_session_id,
            run_state=run_state,
        )
        runner = run_pipeline_mission if mission_data.get("use_pipeline") else run_autonomous_mission
        return runner(
            mission,
            on_message=handler,
            linked_sessions=linked,
            parent_session_id=parent,
            session_id=retry_session_id,
            max_completion_retries=max_retries,
            should_cancel=run_state.should_cancel,
        )

    return _target


def _start_mission(mission_data: dict[str, Any], *, retry_session_id: str | None = None) -> None:
    if not _render_env_banner():
        return
    if not _check_demo_mission_limit():
        return

    st.session_state.activity = []
    st.session_state.streamed_answer = ""
    st.session_state.running = True
    st.session_state["live_cost_usd"] = None
    label = "Retrying mission..." if retry_session_id else "Research in progress..."
    run = create_background_run(
        "mission",
        label,
        _mission_target(mission_data, retry_session_id=retry_session_id),
    )
    st.session_state.active_run_id = run.id
    st.rerun()


def _follow_up_target(session_id: str, payload: dict[str, Any]):
    def _target(run_state: BackgroundRun):
        run_state.session_id = session_id
        handler = _activity_handler_factory([], session_id=session_id, run_state=run_state)
        return run_follow_up_mission(
            session_id,
            payload["prompt"],
            payload["deliverables"],
            on_message=handler,
            max_completion_retries=int(payload.get("max_retries", 1)),
            should_cancel=run_state.should_cancel,
        )

    return _target


def _start_follow_up(session_id: str, payload: dict[str, Any]) -> None:
    if not _render_env_banner():
        return
    if not _check_demo_mission_limit():
        return

    st.session_state.activity = []
    st.session_state.streamed_answer = ""
    st.session_state.running = True
    st.session_state["live_cost_usd"] = None
    run = create_background_run(
        "follow_up",
        "Follow-up in progress...",
        _follow_up_target(session_id, payload),
    )
    st.session_state.active_run_id = run.id
    st.rerun()


def _render_background_run() -> bool:
    """Render an active background run. Returns True when it owns the main panel."""
    run = get_background_run(st.session_state.get("active_run_id"))
    if run is None:
        st.session_state.running = False
        return False

    snapshot = run.snapshot()
    status_text = str(snapshot["status"])
    is_terminal = status_text in TERMINAL_STATUSES
    label = str(snapshot["label"])
    state = "running"
    if status_text == "completed":
        state = "complete"
    elif status_text in {"error", "cancelled"}:
        state = "error"

    with st.status(label, expanded=not is_terminal, state=state) as status:
        if snapshot["live_cost_usd"] is not None:
            st.caption(f"Running cost estimate: ${snapshot['live_cost_usd']:.4f}")
        if snapshot["activity"]:
            render_activity_log(snapshot["activity"])
        if snapshot["streamed_answer"]:
            st.markdown(snapshot["streamed_answer"])

        if not is_terminal:
            if st.button("Cancel run", key=f"cancel_run_{run.id}"):
                run.request_cancel()
                if snapshot["session_id"]:
                    update_session(snapshot["session_id"], status="cancelled", error="Cancelled by user")
                st.warning("Cancellation requested.")
                st.rerun()
            st.caption("This page refreshes while the background run is active.")
            time.sleep(1)
            st.rerun()

        result = snapshot.get("result", run.result)
        if status_text == "cancelled":
            status.update(label="Cancelled", state="error")
            st.warning("Research run was cancelled.")
        elif status_text == "error":
            status.update(label="Run failed", state="error")
            st.error(snapshot["error"] or "An error occurred during the run.")
        elif status_text == "completed" and result is not None:
            if getattr(result, "clarification_needed", False):
                status.update(label="Clarification needed", state="error")
                st.warning(result.answer or "Specify deliverables and try again.")
            else:
                status.update(label="Run complete", state="complete")
                st.success("Run finished.")
                missing = list(getattr(result, "missing_deliverables", []) or [])
                if missing:
                    st.warning("Missing deliverables: " + ", ".join(missing))

    if is_terminal:
        result = snapshot.get("result", run.result)
        if result is not None:
            st.session_state.last_result = result
            if getattr(result, "session_id", None):
                st.session_state.selected_session_id = result.session_id
                st.session_state.view_mode = "session"
        st.session_state.running = False
        st.session_state.activity = snapshot["activity"]
        st.session_state.streamed_answer = snapshot["streamed_answer"]
        st.session_state["live_cost_usd"] = snapshot["live_cost_usd"]
        st.session_state.pop("prefill_linked", None)
        st.session_state.pop("prefill_parent", None)
        st.session_state.pop("prefill_mission", None)
        forget_background_run(run.id)
        st.session_state.active_run_id = None
        st.rerun()

    return True


def _render_session_links(session_id: str) -> None:
    session = load_session(session_id)
    if session.linked_sessions or session.parent_session_id:
        st.markdown("**Linked from:**")
        if session.parent_session_id:
            if st.button(f"Open parent: {session.parent_session_id[:40]}...", key=f"open_parent_{session_id}"):
                _open_session(session.parent_session_id)
        for link_id in session.linked_sessions:
            if st.button(f"Open linked: {link_id[:40]}...", key=f"open_link_{session_id}_{link_id}"):
                _open_session(link_id)

    refs = find_referencing_sessions(session_id)
    if refs:
        st.markdown("**Referenced by:**")
        for ref in refs:
            if st.button(f"Open: {ref.display_title()}", key=f"open_ref_{session_id}_{ref.id}"):
                _open_session(ref.id)


def _render_session_actions(session_id: str) -> None:
    session = load_session(session_id)
    cols = st.columns(5)
    with cols[0]:
        if st.button("Retry", help="Re-run mission in same session folder"):
            st.session_state.retry_session_id = session_id
            st.rerun()
    with cols[1]:
        if st.button("Duplicate", help="Copy settings to new query form"):
            st.session_state.view_mode = "new"
            st.session_state.prefill_mission = mission_dict_from_session(session)
            st.session_state.selected_session_id = None
            st.rerun()
    with cols[2]:
        if st.button("Branch", help="New query linked to this session"):
            st.session_state.view_mode = "new"
            st.session_state.prefill_linked = [session_id]
            st.session_state.prefill_parent = session_id
            st.session_state.selected_session_id = None
            st.rerun()
    with cols[3]:
        try:
            zip_bytes = export_session_zip_enhanced(session_id)
            st.download_button(
                "Export ZIP",
                data=zip_bytes,
                file_name=f"{session.id}.zip",
                mime="application/zip",
            )
        except OSError as exc:
            st.error(f"Export failed for `{session_id}`: {exc}")
    with cols[4]:
        if session.status == "error" and st.button("Delete", help="Delete this session"):
            st.session_state.delete_target = session_id
            st.session_state.delete_target_title = session.display_title()
            st.rerun()


def _render_session_metadata(session_id: str) -> None:
    session = load_session(session_id)
    with st.expander("Session settings", expanded=False):
        new_title = st.text_input("Custom title", value=session.title or "")
        new_notes = st.text_area("Notes", value=session.notes or "", height=80)
        tags_raw = st.text_input("Tags (comma-separated)", value=", ".join(session.tags))
        if st.button("Save settings"):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            update_session(session_id, title=new_title or None, notes=new_notes or None, tags=tags)
            st.success("Saved.")
            st.rerun()


def _render_cost_footer(session_id: str) -> None:
    session = load_session(session_id)
    parts: list[str] = []
    if session.num_turns is not None:
        parts.append(f"Turns: {session.num_turns}")
    if session.total_cost_usd is not None:
        parts.append(f"Cost: ${session.total_cost_usd:.4f}")
    if parts:
        st.caption(" · ".join(parts))


def _render_session_detail(session_id: str) -> None:
    try:
        session = load_session(session_id)
    except FileNotFoundError:
        st.error("Session not found.")
        return

    if st.session_state.pop("retry_session_id", None) == session_id:
        mission_data = mission_dict_from_session(session)
        mission_data["linked_sessions"] = session.linked_sessions
        mission_data["parent_session_id"] = session.parent_session_id
        _start_mission(mission_data, retry_session_id=session_id)
        return

    render_header(
        title=session.display_title(),
        subtitle=f"{session.field} · {session.created_at[:19].replace('T', ' ')} UTC",
    )
    st.markdown(status_badge(session.status), unsafe_allow_html=True)
    _render_cost_footer(session_id)

    if session.deliverables:
        st.caption("Deliverables: " + ", ".join(session.deliverables))
    if session.tags:
        st.caption("Tags: " + ", ".join(session.tags))

    if session.status == "error" and session.error:
        st.error(session.error)

    last_result = st.session_state.get("last_result")
    missing: list[str] = []
    assumptions: list[str] = []
    if last_result and getattr(last_result, "session_id", None) == session_id:
        missing = list(getattr(last_result, "missing_deliverables", []) or [])
        assumptions = list(getattr(last_result, "assumptions", []) or [])
    if not assumptions:
        from deep_research.session_context import load_completion

        completion = load_completion(session)
        if completion:
            assumptions = [str(a) for a in (completion.get("assumptions") or [])]
    render_session_warnings(missing_deliverables=missing, assumptions=assumptions)

    if session.scope:
        st.caption(f"Scope: {session.scope}")
    if session.constraints:
        st.caption(f"Constraints: {session.constraints}")

    _render_session_actions(session_id)
    _render_session_links(session_id)
    _render_session_metadata(session_id)

    tabs = st.tabs(["Answer", "Papers", "Report", "Mind map", "Slides", "Completion", "Activity"])
    with tabs[0]:
        render_turn_timeline(session)
        render_sources_panel(session)
        follow_up = render_follow_up_form(session)
        if follow_up and not st.session_state.running:
            _start_follow_up(session_id, follow_up)

    with tabs[1]:
        render_papers_tab(session)
    with tabs[2]:
        render_report_tab(session)
    with tabs[3]:
        render_mindmap_tab(session)
    with tabs[4]:
        render_slides_tab(session)
    with tabs[5]:
        render_completion_tab(session)
    with tabs[6]:
        activity = load_activity(session_id)
        if st.session_state.last_result and st.session_state.last_result.session_id == session_id:
            activity = activity + st.session_state.get("activity", [])
        render_activity_log(activity)


def main() -> None:
    apply_page_config()
    inject_styles()
    _init_state()
    if not render_demo_gate():
        render_legal_footer()
        return
    _sync_query_params()
    if "demo_purge_done" not in st.session_state:
        purged = purge_expired_demo_sessions()
        st.session_state.demo_purge_done = True
        if purged:
            st.session_state.demo_purged_count = len(purged)
    if "stale_sweep_done" not in st.session_state:
        stale = mark_stale_running_sessions()
        st.session_state.stale_sweep_done = True
        if stale:
            st.session_state.stale_sweep_count = len(stale)

    if st.session_state.get("stale_sweep_count"):
        st.warning(
            f"Recovered {st.session_state['stale_sweep_count']} stale running session(s). "
            "They were marked interrupted so you can retry them."
        )

    render_demo_banner()
    selected_id = render_session_browser()
    ui_mode = st.session_state.get("ui_mode", "Full mission")

    if _render_background_run():
        render_legal_footer()
        return

    if ui_mode == "Quick query" and st.session_state.view_mode != "session":
        render_header(title="Quick Research", subtitle="Phase 1 — one-shot query, no session artifacts.")
        if _render_env_banner():
            payload = render_quick_query_mode()
            if payload and not st.session_state.running:
                _start_quick_query(payload)
        render_legal_footer()
        return

    if ui_mode == "Guided chat" and st.session_state.view_mode != "session":
        render_header(title="Guided Chat", subtitle="Phase 2 — multi-turn conversation with memory.")
        if _render_env_banner():
            payload = render_chat_mode()
            if payload and not st.session_state.running:
                _start_chat(payload)
        render_legal_footer()
        return

    if st.session_state.view_mode == "session" and selected_id:
        _render_session_detail(selected_id)
        render_legal_footer()
        return

    render_header(
        title="New Research",
        subtitle="Phase 3 — full autonomous mission with deliverables and session artifacts.",
    )

    if not _render_env_banner():
        return

    prefill = st.session_state.get("prefill_mission")
    template_data = render_template_picker()
    if template_data and not prefill:
        prefill = template_data
    mission_data = render_mission_form(prefill=prefill, public_demo=is_public_demo())
    if mission_data and not st.session_state.running:
        _start_mission(mission_data)

    render_legal_footer()


if __name__ == "__main__":
    main()
