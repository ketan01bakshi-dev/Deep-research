"""Background run registry tests."""

from __future__ import annotations

from deep_research.web.background_runs import (
    TERMINAL_STATUSES,
    create_background_run,
    forget_background_run,
    get_background_run,
)


def test_background_run_completes_with_result():
    from deep_research.types import AutonomousResearchResult

    def target(run):
        assert run.status == "running"
        run.add_activity("[status] started")
        return AutonomousResearchResult(
            question="Q",
            answer="A",
            session_id="sess-1",
            num_turns=1,
            total_cost_usd=0.0,
            is_error=False,
            subtype="success",
        )

    run = create_background_run("mission", "Test", target)
    run._thread.join(timeout=2)
    snapshot = run.snapshot()

    assert snapshot["status"] == "completed"
    assert snapshot["session_id"] == "sess-1"
    assert snapshot["activity"] == ["[status] started"]
    assert snapshot["status"] in TERMINAL_STATUSES
    assert snapshot["result"] is not None
    assert snapshot["result"].answer == "A"
    assert snapshot["result"].session_id == "sess-1"
    assert get_background_run(run.id) is run
    forget_background_run(run.id)
    assert get_background_run(run.id) is None


def test_background_run_cancel_request_sets_flag():
    run = create_background_run("mission", "Waiting", lambda run: None)
    run.request_cancel()
    assert run.should_cancel()
    assert run.snapshot()["cancel_requested"] is True
    forget_background_run(run.id)
