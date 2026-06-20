"""Shared run/job registry for Streamlit, API, and scheduler."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agent_core.io import save_json

TERMINAL_STATUSES = frozenset({"completed", "error", "cancelled"})
RUN_STATUSES = frozenset({"pending", "running", "cancelling", *TERMINAL_STATUSES})


@dataclass(slots=True)
class RunRecord:
    """Mutable state for one long-running action."""

    id: str
    kind: str
    label: str
    status: str = "pending"
    activity: list[str] = field(default_factory=list)
    streamed_answer: str = ""
    live_cost_usd: float | None = None
    result: Any | None = None
    error: str | None = None
    session_id: str | None = None
    payload: dict[str, Any] | None = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def request_cancel(self) -> None:
        with self._lock:
            self._cancel_event.set()
            if self.status not in TERMINAL_STATUSES:
                self.status = "cancelling"

    def should_cancel(self) -> bool:
        return self._cancel_event.is_set()

    def add_activity(self, entry: str) -> None:
        with self._lock:
            self.activity.append(entry)

    def set_streamed_answer(self, answer: str) -> None:
        with self._lock:
            self.streamed_answer = answer

    def set_live_cost(self, cost: float) -> None:
        with self._lock:
            self.live_cost_usd = cost

    def finish(self, result: Any) -> None:
        subtype = getattr(result, "subtype", None)
        is_error = bool(getattr(result, "is_error", False))
        with self._lock:
            self.result = result
            self.session_id = getattr(result, "session_id", None) or self.session_id
            self.error = getattr(result, "error", None)
            if subtype == "cancelled":
                self.status = "cancelled"
            elif is_error:
                self.status = "error"
            else:
                self.status = "completed"
            self.completed_at = datetime.now(timezone.utc).isoformat()

    def fail(self, exc: BaseException) -> None:
        with self._lock:
            self.status = "error"
            self.error = str(exc)
            self.completed_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "id": self.id,
                "kind": self.kind,
                "label": self.label,
                "status": self.status,
                "activity": list(self.activity),
                "streamed_answer": self.streamed_answer,
                "live_cost_usd": self.live_cost_usd,
                "result": self.result,
                "error": self.error,
                "session_id": self.session_id,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "cancel_requested": self.should_cancel(),
            }

    def start(self, target: Callable[["RunRecord"], Any]) -> None:
        with self._lock:
            if self._thread is not None:
                return
            self.status = "running"
            self._thread = threading.Thread(
                target=_run_target,
                args=(self, target),
                name=f"deep-research-{self.kind}-{self.id}",
                daemon=True,
            )
            self._thread.start()


class RunRegistry:
    """Thread-safe registry with optional JSON persistence."""

    def __init__(self, persist_path: Path | None = None) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load()

    def _serializable(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        with self._lock:
            for run_id, run in self._runs.items():
                snap = run.snapshot()
                snap.pop("result", None)
                if run.payload:
                    snap["payload"] = run.payload
                if run.result is not None:
                    snap["answer"] = getattr(run.result, "answer", None)
                    snap["missing_deliverables"] = list(
                        getattr(run.result, "missing_deliverables", []) or []
                    )
                    snap["assumptions"] = list(getattr(run.result, "assumptions", []) or [])
                out[run_id] = snap
        return out

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            save_json(self._persist_path, self._serializable())
        except OSError:
            pass

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        with self._lock:
            for run_id, fields in data.items():
                if not isinstance(fields, dict):
                    continue
                run = RunRecord(
                    id=str(run_id),
                    kind=str(fields.get("kind") or "mission"),
                    label=str(fields.get("label") or "Restored run"),
                    status=str(fields.get("status") or "error"),
                    session_id=fields.get("session_id"),
                    error=fields.get("error"),
                    payload=fields.get("payload"),
                    started_at=str(fields.get("started_at") or datetime.now(timezone.utc).isoformat()),
                    completed_at=fields.get("completed_at"),
                )
                self._runs[run_id] = run

    def create(
        self,
        kind: str,
        label: str,
        *,
        target: Callable[[RunRecord], Any] | None = None,
        session_id: str | None = None,
        payload: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> RunRecord:
        run = RunRecord(
            id=run_id or uuid.uuid4().hex[:12],
            kind=kind,
            label=label,
            session_id=session_id,
            payload=payload,
        )
        with self._lock:
            self._runs[run.id] = run
        self._persist()
        if target is not None:
            run.start(target)
        return run

    def get(self, run_id: str | None) -> RunRecord | None:
        if not run_id:
            return None
        with self._lock:
            return self._runs.get(run_id)

    def forget(self, run_id: str | None) -> None:
        if not run_id:
            return
        with self._lock:
            self._runs.pop(run_id, None)
        self._persist()

    def update(self, run_id: str, **fields: Any) -> RunRecord | None:
        run = self.get(run_id)
        if run is None:
            return None
        with run._lock:
            for key, value in fields.items():
                if hasattr(run, key):
                    setattr(run, key, value)
        self._persist()
        return run

    def list_runs(self) -> list[RunRecord]:
        with self._lock:
            return list(self._runs.values())


def _run_target(run: RunRecord, target: Callable[[RunRecord], Any]) -> None:
    try:
        result = target(run)
        if result is not None:
            run.finish(result)
    except BaseException as exc:
        run.fail(exc)


def status_from_result(result: Any) -> str:
    if getattr(result, "subtype", None) == "cancelled":
        return "cancelled"
    return "completed" if not getattr(result, "is_error", False) else "error"
