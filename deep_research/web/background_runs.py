"""In-process background run registry for Streamlit workflows."""

from __future__ import annotations

from typing import Any, Callable

from deep_research.run_registry import (
    TERMINAL_STATUSES,
    RunRecord,
    RunRegistry,
)

# Streamlit UI runs are ephemeral; no disk persistence required.
_registry = RunRegistry(persist_path=None)

# Backward-compatible alias
BackgroundRun = RunRecord


def create_background_run(kind: str, label: str, target: Callable[[RunRecord], Any]) -> RunRecord:
    return _registry.create(kind, label, target=target)


def get_background_run(run_id: str | None) -> RunRecord | None:
    return _registry.get(run_id)


def forget_background_run(run_id: str | None) -> None:
    _registry.forget(run_id)
