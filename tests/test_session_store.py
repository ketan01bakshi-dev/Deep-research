"""Session store round-trip tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from deep_research.autonomous_mission import ResearchMission
from deep_research.session_context import (
    SESSION_LIST_SKIP_DIRS,
    append_activity,
    append_turn,
    create_session,
    is_stale_running_session,
    list_sessions,
    list_unreadable_session_meta,
    load_activity,
    load_session,
    load_turns,
    mark_stale_running_sessions,
    update_session,
    SessionTurn,
)


def test_session_crud_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", tmp_path / "Research")

    mission = ResearchMission(
        topic="CRUD test",
        field="science",
        objectives=["Verify session store"],
        deliverables=["answer"],
        scope="Unit test scope",
        constraints="None",
        success_criteria=["Session persists"],
    )
    session = create_session(mission, status="pending")
    update_session(session.id, status="running", title="Custom title")
    append_activity(session.id, "[tool] search_research_literature")
    append_turn(
        session.id,
        SessionTurn(
            prompt="CRUD test",
            answer="Done",
            at="2026-06-13T00:00:00+00:00",
            deliverables=["answer"],
        ),
    )

    loaded = load_session(session.id)
    assert loaded.status == "running"
    assert loaded.title == "Custom title"
    assert loaded.scope == "Unit test scope"
    assert loaded.success_criteria == ["Session persists"]
    assert load_activity(session.id) == ["[tool] search_research_literature"]
    turns = load_turns(session.id)
    assert len(turns) == 1
    assert turns[0].answer == "Done"


def _patch_research_dirs(monkeypatch, tmp_path):
    research = tmp_path / "Research"
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", research)
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", research)
    research.mkdir(parents=True, exist_ok=True)
    return research


def test_list_sessions_excludes_latest_mirror(tmp_path, monkeypatch):
    research = _patch_research_dirs(monkeypatch, tmp_path)

    mission = ResearchMission(
        topic="Diabetes cure research",
        field="health",
        objectives=["Survey"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="completed")

    latest = research / "latest"
    latest.mkdir()
    mirror_meta = {
        **json.loads((session.root / "meta.json").read_text(encoding="utf-8")),
        "root": str(latest.relative_to(tmp_path)),
        "source_session_id": session.id,
    }
    (latest / "meta.json").write_text(json.dumps(mirror_meta), encoding="utf-8")

    listed = list_sessions()
    ids = [s.id for s in listed]

    assert session.id in ids
    assert ids.count(session.id) == 1
    assert "latest" in SESSION_LIST_SKIP_DIRS
    assert all(s.root.name != "latest" for s in listed)


def test_list_sessions_returns_unique_ids(tmp_path, monkeypatch):
    research = _patch_research_dirs(monkeypatch, tmp_path)

    mission = ResearchMission(
        topic="Unique ids",
        field="science",
        objectives=["Test"],
        deliverables=["answer"],
    )
    session = create_session(mission, status="completed")

    duplicate_dir = research / f"duplicate_{session.id}"
    duplicate_dir.mkdir()
    (duplicate_dir / "meta.json").write_text(
        (session.root / "meta.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    listed = list_sessions()
    assert len(listed) == 1
    assert listed[0].id == session.id
    assert listed[0].root.name == session.id


def test_mark_stale_running_sessions_marks_only_old_running(tmp_path, monkeypatch):
    _patch_research_dirs(monkeypatch, tmp_path)
    old_now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)

    stale = create_session(
        ResearchMission("Old run", "science", ["Test"], ["answer"]),
        status="running",
    )
    fresh = create_session(
        ResearchMission("Fresh run", "science", ["Test"], ["answer"]),
        status="running",
    )
    done = create_session(
        ResearchMission("Done run", "science", ["Test"], ["answer"]),
        status="completed",
    )
    update_session(stale.id, created_at=(old_now - timedelta(hours=8)).isoformat())
    update_session(fresh.id, created_at=(old_now - timedelta(minutes=10)).isoformat())
    update_session(done.id, created_at=(old_now - timedelta(hours=8)).isoformat())

    assert is_stale_running_session(load_session(stale.id), now=old_now)
    marked = mark_stale_running_sessions(now=old_now)

    assert [s.id for s in marked] == [stale.id]
    assert load_session(stale.id).status == "error"
    assert "stale running session" in (load_session(stale.id).error or "")
    assert load_session(fresh.id).status == "running"
    assert load_session(done.id).status == "completed"


def test_list_sessions_field_and_deliverable_filters(tmp_path, monkeypatch):
    _patch_research_dirs(monkeypatch, tmp_path)
    a = create_session(
        ResearchMission("Health topic", "health", ["Test"], ["answer", "report"]),
        status="completed",
    )
    create_session(
        ResearchMission("Science topic", "science", ["Test"], ["answer"]),
        status="completed",
    )
    update_session(a.id, tags=["diabetes"])

    health_only = list_sessions(field_filter="health")
    assert [s.id for s in health_only] == [a.id]
    report_only = list_sessions(deliverable_filter="report")
    assert [s.id for s in report_only] == [a.id]
    tagged = list_sessions(tag_filter="diabetes")
    assert [s.id for s in tagged] == [a.id]


def test_list_unreadable_session_meta_reports_bad_json(tmp_path, monkeypatch):
    research = _patch_research_dirs(monkeypatch, tmp_path)
    bad = research / "bad-session"
    bad.mkdir()
    (bad / "meta.json").write_text("{not-json", encoding="utf-8")

    unreadable = list_unreadable_session_meta()

    assert unreadable == [bad / "meta.json"]

