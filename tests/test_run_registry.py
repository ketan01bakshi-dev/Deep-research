"""Shared run registry tests."""

from __future__ import annotations

from deep_research.run_registry import RunRecord, RunRegistry, status_from_result
from deep_research.types import AutonomousResearchResult

# Keys app.py reads from RunRecord.snapshot() in _render_background_run.
APP_SNAPSHOT_KEYS = frozenset(
    {
        "status",
        "label",
        "activity",
        "streamed_answer",
        "live_cost_usd",
        "session_id",
        "result",
        "error",
    }
)


def test_run_registry_persists_and_cancels(tmp_path):
    registry = RunRegistry(persist_path=tmp_path / "jobs.json")

    def target(run):
        return AutonomousResearchResult(
            question="Q",
            answer="A",
            session_id="sess-1",
            num_turns=1,
            total_cost_usd=0.0,
            is_error=False,
            subtype="success",
        )

    run = registry.create("mission", "Test", target=target)
    run._thread.join(timeout=2)
    snapshot = registry.get(run.id).snapshot()
    assert snapshot["status"] == "completed"
    assert snapshot["result"] is not None
    assert snapshot["result"].session_id == "sess-1"
    assert (tmp_path / "jobs.json").exists()

    cancel_run = registry.create("mission", "Cancel me")
    cancel_run.request_cancel()
    assert cancel_run.should_cancel()


def test_snapshot_includes_result_key_for_app_contract():
    run = RunRecord(id="run-1", kind="mission", label="Test")
    snapshot = run.snapshot()
    assert "result" in snapshot
    assert snapshot["result"] is None

    result = AutonomousResearchResult(
        question="Q",
        answer="Done",
        session_id="sess-9",
        num_turns=1,
        total_cost_usd=0.0,
        is_error=False,
        subtype="success",
    )
    run.finish(result)
    snapshot = run.snapshot()
    assert snapshot["result"] is result
    assert snapshot["result"].answer == "Done"
    for key in APP_SNAPSHOT_KEYS:
        assert key in snapshot, f"snapshot missing key required by app.py: {key!r}"


def test_snapshot_result_none_while_running():
    run = RunRecord(id="run-2", kind="mission", label="In flight", status="running")
    assert run.snapshot()["result"] is None


def test_snapshot_result_none_after_fail():
    run = RunRecord(id="run-3", kind="mission", label="Boom")
    run.fail(RuntimeError("boom"))
    snapshot = run.snapshot()
    assert snapshot["status"] == "error"
    assert snapshot["error"] == "boom"
    assert snapshot["result"] is None
    for key in APP_SNAPSHOT_KEYS:
        assert key in snapshot


def test_status_from_result_cancelled():
    result = AutonomousResearchResult(
        question="Q",
        answer=None,
        session_id="s",
        num_turns=0,
        total_cost_usd=None,
        is_error=True,
        subtype="cancelled",
        error="Cancelled by user",
    )
    assert status_from_result(result) == "cancelled"
