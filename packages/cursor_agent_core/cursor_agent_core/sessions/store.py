"""Generic session folder store for Cursor SDK agents."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cursor_agent_core.paths.file_helpers import ensure_dir, slugify
from agent_core.io import atomic_write_text, save_json


@dataclass(slots=True)
class SessionRecord:
    """Minimal session metadata stored in meta.json."""

    id: str
    status: str
    created_at: str
    root: Path
    title: str | None = None
    answer: str | None = None
    agent_id: str | None = None
    error: str | None = None
    pinned: bool = False
    tags: list[str] | None = None
    notes: str | None = None
    extra: dict[str, Any] | None = None

    @property
    def meta_path(self) -> Path:
        return self.root / "meta.json"

    @property
    def turns_path(self) -> Path:
        return self.root / "turns.json"

    @property
    def activity_path(self) -> Path:
        return self.root / "activity.json"

    def display_title(self) -> str:
        return (self.title or self.id).strip()


class SessionStore:
    """CRUD for per-session folders under a sessions directory."""

    def __init__(
        self,
        sessions_dir: Path,
        *,
        project_root: Path | None = None,
        id_factory: Callable[[], str] | None = None,
        subdirs: tuple[str, ...] = (),
    ) -> None:
        self.sessions_dir = ensure_dir(sessions_dir)
        self.project_root = project_root or sessions_dir.parent.parent
        self.id_factory = id_factory or self._default_id
        self.subdirs = subdirs

    @staticmethod
    def _default_id() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{stamp}_session"

    def _write_meta(self, record: SessionRecord, data: dict[str, Any]) -> None:
        atomic_write_text(record.meta_path, json.dumps(data, indent=2))

    def create(
        self,
        *,
        session_id: str | None = None,
        status: str = "pending",
        title: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> SessionRecord:
        sid = session_id or self.id_factory()
        root = ensure_dir(self.sessions_dir / sid)
        for name in self.subdirs:
            ensure_dir(root / name)

        record = SessionRecord(
            id=sid,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
            root=root,
            title=title,
            extra=extra or {},
        )
        meta = {
            "id": record.id,
            "status": record.status,
            "created_at": record.created_at,
            "root": str(record.root.relative_to(self.project_root)),
            "title": record.title,
            "answer": record.answer,
            "agent_id": record.agent_id,
            "error": record.error,
            "pinned": record.pinned,
            "tags": record.tags or [],
            "notes": record.notes,
            **(extra or {}),
        }
        self._write_meta(record, meta)
        self.save_turns(sid, [])
        self.save_activity(sid, [])
        return record

    def load(self, session_id: str) -> SessionRecord:
        meta_path = self.sessions_dir / session_id / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        root = self.project_root / str(data["root"])
        known = {"id", "status", "created_at", "root", "title", "answer", "agent_id", "error", "pinned", "tags", "notes"}
        extra = {k: v for k, v in data.items() if k not in known}
        return SessionRecord(
            id=str(data["id"]),
            status=str(data.get("status") or "unknown"),
            created_at=str(data.get("created_at") or ""),
            root=root,
            title=data.get("title"),
            answer=data.get("answer"),
            agent_id=data.get("agent_id"),
            error=data.get("error"),
            pinned=bool(data.get("pinned", False)),
            tags=list(data.get("tags") or []),
            notes=data.get("notes"),
            extra=extra,
        )

    def update(self, session_id: str, **fields: Any) -> SessionRecord:
        record = self.load(session_id)
        data = json.loads(record.meta_path.read_text(encoding="utf-8"))
        for key, value in fields.items():
            if key in data or key in ("title", "answer", "agent_id", "error", "pinned", "tags", "notes", "status"):
                data[key] = value
            elif record.extra is not None:
                data[key] = value
        atomic_write_text(record.meta_path, json.dumps(data, indent=2))
        return self.load(session_id)

    def delete(self, session_id: str) -> None:
        record = self.load(session_id)
        if record.root.exists():
            shutil.rmtree(record.root)

    def list(
        self,
        *,
        search: str = "",
        status_filter: str = "all",
    ) -> list[SessionRecord]:
        if not self.sessions_dir.exists():
            return []

        sessions: list[SessionRecord] = []
        for entry in self.sessions_dir.iterdir():
            if not entry.is_dir():
                continue
            meta_path = entry / "meta.json"
            if not meta_path.exists():
                continue
            try:
                sessions.append(self.load(entry.name))
            except (json.JSONDecodeError, KeyError, OSError):
                continue

        query = search.strip().lower()
        if query:
            sessions = [
                s
                for s in sessions
                if query in s.display_title().lower()
                or query in s.id.lower()
            ]

        if status_filter and status_filter != "all":
            sessions = [s for s in sessions if s.status == status_filter]

        sessions.sort(key=lambda s: s.created_at, reverse=True)
        sessions.sort(key=lambda s: s.pinned, reverse=True)
        return sessions

    def load_turns(self, session_id: str) -> list[dict[str, Any]]:
        record = self.load(session_id)
        if not record.turns_path.exists():
            return []
        data = json.loads(record.turns_path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []

    def save_turns(self, session_id: str, turns: list[dict[str, Any]]) -> None:
        record = self.load(session_id)
        save_json(record.turns_path, turns)

    def append_turn(self, session_id: str, turn: dict[str, Any]) -> None:
        turns = self.load_turns(session_id)
        turns.append(turn)
        self.save_turns(session_id, turns)

    def load_activity(self, session_id: str) -> list[str]:
        record = self.load(session_id)
        if not record.activity_path.exists():
            return []
        data = json.loads(record.activity_path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []

    def save_activity(self, session_id: str, entries: list[str]) -> None:
        record = self.load(session_id)
        save_json(record.activity_path, entries)

    def append_activity(self, session_id: str, entry: str) -> None:
        entries = self.load_activity(session_id)
        entries.append(entry)
        self.save_activity(session_id, entries[-200:])

    def export_zip(self, session_id: str) -> bytes:
        record = self.load(session_id)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in record.root.rglob("*"):
                if path.is_file():
                    archive.write(path, arcname=path.relative_to(record.root))
        buffer.seek(0)
        return buffer.getvalue()

    def list_files(self, session_id: str, subdir: str) -> list[Path]:
        record = self.load(session_id)
        directory = record.root / subdir
        if not directory.exists():
            return []
        return sorted(
            (p for p in directory.iterdir() if p.is_file()),
            key=lambda p: p.name.lower(),
        )
