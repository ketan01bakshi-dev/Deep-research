"""Tests for public demo configuration and limits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from deep_research.autonomous_mission import ResearchMission
from deep_research.demo_config import (
    DEFAULT_MAX_DEMO_MISSIONS_PER_DAY,
    allowed_deliverables,
    can_start_demo_mission,
    demo_missions_remaining,
    is_public_demo,
    max_demo_missions_per_day,
    record_demo_mission_start,
)
from deep_research.demo_limits import purge_expired_demo_sessions
from deep_research.session_context import create_session, load_session


def test_is_public_demo_false_by_default(monkeypatch):
    monkeypatch.delenv("PUBLIC_DEMO", raising=False)
    assert is_public_demo() is False


def test_is_public_demo_true(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "true")
    assert is_public_demo() is True


def test_allowed_deliverables_restricted_in_demo(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "true")
    monkeypatch.setenv("DEMO_ALLOWED_DELIVERABLES", "answer")
    assert allowed_deliverables() == frozenset({"answer"})


def test_demo_mission_quota(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "true")
    monkeypatch.setenv("MAX_DEMO_MISSIONS_PER_DAY", "2")
    monkeypatch.setattr("deep_research.demo_config.DEMO_USAGE_FILE", tmp_path / "usage.json")

    assert can_start_demo_mission() is True
    record_demo_mission_start()
    record_demo_mission_start()
    assert can_start_demo_mission() is False
    assert demo_missions_remaining() == 0


def test_max_demo_missions_defaults(monkeypatch):
    monkeypatch.delenv("MAX_DEMO_MISSIONS_PER_DAY", raising=False)
    assert max_demo_missions_per_day() == DEFAULT_MAX_DEMO_MISSIONS_PER_DAY


def test_purge_expired_demo_sessions(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "true")
    monkeypatch.setenv("DEMO_SESSION_TTL_HOURS", "1")
    monkeypatch.setattr("deep_research.session_context.RESEARCH_DIR", tmp_path / "Research")
    monkeypatch.setattr("deep_research.session_context.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("deep_research.tools.paths.RESEARCH_DIR", tmp_path / "Research")

    old_time = datetime.now(timezone.utc) - timedelta(hours=5)
    session = create_session(
        ResearchMission("Old topic", "science", ["Test"], ["answer"]),
        status="completed",
    )
    from deep_research.session_context import update_session

    update_session(session.id, created_at=old_time.isoformat())
    assert load_session(session.id).id == session.id

    deleted = purge_expired_demo_sessions()
    assert session.id in deleted

    with pytest.raises(FileNotFoundError):
        load_session(session.id)


def test_purge_skipped_when_not_public_demo(tmp_path, monkeypatch):
    monkeypatch.delenv("PUBLIC_DEMO", raising=False)
    assert purge_expired_demo_sessions() == []
