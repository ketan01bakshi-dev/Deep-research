"""Contract tests — Streamlit app and runners must stay in sync."""

from __future__ import annotations

import inspect

import pytest

# Keywords app.py passes to either run_autonomous_mission or run_pipeline_mission
APP_RUNNER_KWARGS = frozenset(
    {
        "on_message",
        "linked_sessions",
        "parent_session_id",
        "session_id",
        "max_completion_retries",
        "should_cancel",
    }
)


@pytest.mark.parametrize(
    "runner",
    [
        pytest.param("run_autonomous_mission", id="autonomous"),
        pytest.param("run_pipeline_mission", id="pipeline"),
    ],
)
def test_runner_accepts_app_kwargs(runner: str):
    if runner == "run_autonomous_mission":
        from deep_research.autonomous import run_autonomous_mission as fn
    else:
        from deep_research.pipeline import run_pipeline_mission as fn

    sig = inspect.signature(fn)
    params = set(sig.parameters) - {"mission"}
    for key in APP_RUNNER_KWARGS:
        assert key in params, f"{fn.__name__} missing parameter {key!r} required by app.py"


def test_cursor_client_requires_workspace():
    from cursor_agent_core.bridge.client import cursor_client

    sig = inspect.signature(cursor_client)
    assert "workspace" in sig.parameters
    assert sig.parameters["workspace"].kind == inspect.Parameter.KEYWORD_ONLY


def test_project_cwd_is_deep_research_root():
    from deep_research.cursor_options import PROJECT_ROOT, project_cwd

    assert project_cwd() == str(PROJECT_ROOT)
    assert (PROJECT_ROOT / "app.py").exists()


def test_snapshot_result_fallback_for_stale_streamlit_cache():
    """app.py uses snapshot.get('result', run.result) when Streamlit caches old snapshot()."""
    from deep_research.run_registry import RunRecord
    from deep_research.types import AutonomousResearchResult

    result = AutonomousResearchResult(
        question="Q",
        answer="A",
        session_id="s",
        num_turns=1,
        total_cost_usd=0.0,
        is_error=False,
        subtype="success",
    )
    run = RunRecord(id="r1", kind="mission", label="L")
    run.finish(result)
    stale_snapshot = {k: v for k, v in run.snapshot().items() if k != "result"}
    assert stale_snapshot.get("result", run.result) is result


def test_run_record_snapshot_matches_app_contract():
    from deep_research.run_registry import RunRecord

    run = RunRecord(id="x", kind="mission", label="L")
    snapshot = run.snapshot()
    for key in (
        "status",
        "label",
        "activity",
        "streamed_answer",
        "live_cost_usd",
        "session_id",
        "result",
        "error",
    ):
        assert key in snapshot, f"RunRecord.snapshot() missing {key!r} required by app._render_background_run"


def test_app_module_imports():
    import importlib

    app = importlib.import_module("app")
    assert hasattr(app, "main")


def test_app_has_session_browser_import():
    import importlib

    app = importlib.import_module("app")
    from deep_research.web.session_browser import render_session_browser

    assert app.render_session_browser is render_session_browser


def test_build_all_custom_tools_includes_core_tools():
    from deep_research.tools import build_all_custom_tools

    tools = build_all_custom_tools()
    assert "complete_mission" in tools
    assert "summarize_downloaded_papers" in tools
    assert "query_session_corpus" in tools


def test_mission_from_dict_accepts_pipeline_flag():
    from deep_research.autonomous_mission import mission_from_dict

    mission = mission_from_dict(
        {
            "topic": "Test",
            "field": "general",
            "objectives": ["Explore"],
            "deliverables": ["answer"],
            "use_pipeline": True,
        }
    )
    assert mission.topic == "Test"
