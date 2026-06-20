"""Web layer import smoke tests (no Streamlit runtime)."""

from __future__ import annotations


def test_web_modules_import():
    from deep_research.web.completion import render_completion_tab
    from deep_research.web.components import render_mission_form
    from deep_research.web.export import export_session_zip_enhanced
    from deep_research.web.modes import render_chat_mode, render_quick_query_mode
    from deep_research.web.session_browser import render_session_browser
    from deep_research.web.templates import list_template_names, load_template

    assert callable(render_completion_tab)
    assert callable(render_mission_form)
    assert callable(export_session_zip_enhanced)
    assert callable(render_chat_mode)
    assert callable(render_quick_query_mode)
    assert callable(render_session_browser)
    assert isinstance(list_template_names(), list)
    assert load_template("__nonexistent__") is None
