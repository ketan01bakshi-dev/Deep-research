"""Per-query research session folders and active-session context."""

from __future__ import annotations

import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deep_research.autonomous_mission import ResearchMission
from deep_research.tools.paths import PROJECT_ROOT, RESEARCH_DIR, ensure_dir, slugify
from cursor_agent_core.sessions import SessionStore

_active_session: ContextVar["ResearchSession | None"] = ContextVar(
    "active_research_session",
    default=None,
)

SESSION_SUBDIRS = ("Papers", "Reports", "Diagrams", "Slides")
MAX_LINKED_SESSIONS = 3
MAX_CONTEXT_ANSWER_CHARS = 4000
STALE_RUNNING_AFTER_SECONDS = 6 * 60 * 60
# Published mirror under docs/Research/latest/ — not a separate browsable session.
SESSION_LIST_SKIP_DIRS = frozenset({"latest"})


def _session_store() -> SessionStore:
    return SessionStore(
        RESEARCH_DIR,
        project_root=PROJECT_ROOT,
        subdirs=SESSION_SUBDIRS,
    )


@dataclass(slots=True)
class SessionTurn:
    """One research turn within a session thread."""

    prompt: str
    answer: str | None
    at: str
    deliverables: list[str]
    is_error: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "answer": self.answer,
            "at": self.at,
            "deliverables": self.deliverables,
            "is_error": self.is_error,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionTurn:
        return cls(
            prompt=str(data.get("prompt") or ""),
            answer=data.get("answer"),
            at=str(data.get("at") or ""),
            deliverables=list(data.get("deliverables") or []),
            is_error=bool(data.get("is_error", False)),
            error=data.get("error"),
        )


@dataclass(slots=True)
class ResearchSession:
    """One user research query with a dedicated folder under Docs/Research/."""

    id: str
    topic: str
    field: str
    deliverables: list[str]
    status: str
    created_at: str
    root: Path
    answer: str | None = None
    agent_id: str | None = None
    error: str | None = None
    title: str | None = None
    pinned: bool = False
    linked_sessions: list[str] = field(default_factory=list)
    parent_session_id: str | None = None
    tags: list[str] = field(default_factory=list)
    notes: str | None = None
    num_turns: int | None = None
    total_cost_usd: float | None = None
    audience: str = "informed lay reader"
    depth: str = "deep"
    objectives: list[str] = field(default_factory=list)
    scope: str | None = None
    constraints: str | None = None
    success_criteria: list[str] = field(default_factory=list)

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
        return (self.title or self.topic).strip()

    def relative_root(self) -> str:
        return str(self.root.relative_to(PROJECT_ROOT))

    def papers_dir(self) -> Path:
        return ensure_dir(self.root / "Papers")

    def reports_dir(self) -> Path:
        return ensure_dir(self.root / "Reports")

    def diagrams_dir(self) -> Path:
        return ensure_dir(self.root / "Diagrams")

    def slides_dir(self) -> Path:
        return ensure_dir(self.root / "Slides")

    def to_meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "field": self.field,
            "deliverables": self.deliverables,
            "status": self.status,
            "created_at": self.created_at,
            "root": self.relative_root(),
            "answer": self.answer,
            "agent_id": self.agent_id,
            "error": self.error,
            "title": self.title,
            "pinned": self.pinned,
            "linked_sessions": self.linked_sessions,
            "parent_session_id": self.parent_session_id,
            "tags": self.tags,
            "notes": self.notes,
            "num_turns": self.num_turns,
            "total_cost_usd": self.total_cost_usd,
            "audience": self.audience,
            "depth": self.depth,
            "objectives": self.objectives,
            "scope": self.scope,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
        }

    @classmethod
    def from_meta(cls, data: dict[str, Any]) -> ResearchSession:
        root = PROJECT_ROOT / str(data["root"])
        return cls(
            id=str(data["id"]),
            topic=str(data.get("topic") or ""),
            field=str(data.get("field") or ""),
            deliverables=list(data.get("deliverables") or []),
            status=str(data.get("status") or "unknown"),
            created_at=str(data.get("created_at") or ""),
            root=root,
            answer=data.get("answer"),
            agent_id=data.get("agent_id"),
            error=data.get("error"),
            title=data.get("title"),
            pinned=bool(data.get("pinned", False)),
            linked_sessions=list(data.get("linked_sessions") or []),
            parent_session_id=data.get("parent_session_id"),
            tags=list(data.get("tags") or []),
            notes=data.get("notes"),
            num_turns=data.get("num_turns"),
            total_cost_usd=data.get("total_cost_usd"),
            audience=str(data.get("audience") or "informed lay reader"),
            depth=str(data.get("depth") or "deep"),
            objectives=list(data.get("objectives") or []),
            scope=data.get("scope"),
            constraints=data.get("constraints"),
            success_criteria=list(data.get("success_criteria") or []),
        )


def _session_id_for_mission(mission: ResearchMission) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:4]
    return f"{stamp}_{mission.slug}_{short}"



def create_session(
    mission: ResearchMission,
    *,
    status: str = "pending",
    linked_sessions: list[str] | None = None,
    parent_session_id: str | None = None,
) -> ResearchSession:
    """Create folder tree and meta.json for a new research query."""
    store = _session_store()
    session_id = _session_id_for_mission(mission)
    links = list(linked_sessions or [])[:MAX_LINKED_SESSIONS]
    extra = {
        "topic": mission.topic,
        "field": mission.field,
        "deliverables": mission.normalized_deliverables(),
        "linked_sessions": links,
        "parent_session_id": parent_session_id,
        "audience": mission.audience,
        "depth": mission.depth,
        "objectives": list(mission.objectives),
        "scope": mission.scope,
        "constraints": mission.constraints,
        "success_criteria": list(mission.success_criteria),
    }
    store.create(session_id=session_id, status=status, title=mission.topic, extra=extra)
    return load_session(session_id)


def set_active_session(session: ResearchSession | None) -> None:
    _active_session.set(session)


def get_active_session() -> ResearchSession | None:
    return _active_session.get()


def clear_active_session() -> None:
    _active_session.set(None)


def load_session(session_id: str) -> ResearchSession:
    record = _session_store().load(session_id)
    data = json.loads(record.meta_path.read_text(encoding="utf-8"))
    return ResearchSession.from_meta(data)


def update_session(session_id: str, **fields: Any) -> ResearchSession:
    _session_store().update(session_id, **fields)
    return load_session(session_id)


def delete_session(session_id: str) -> None:
    _session_store().delete(session_id)


def delete_sessions(session_ids: list[str]) -> int:
    deleted = 0
    for session_id in session_ids:
        try:
            delete_session(session_id)
            deleted += 1
        except FileNotFoundError:
            continue
    return deleted


def delete_failed_sessions() -> int:
    failed = [s.id for s in list_sessions() if s.status == "error"]
    return delete_sessions(failed)


def _parse_session_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_stale_running_session(
    session: ResearchSession,
    *,
    now: datetime | None = None,
    max_age_seconds: int = STALE_RUNNING_AFTER_SECONDS,
) -> bool:
    """Return True when a running session is old enough to be considered interrupted."""
    if session.status != "running":
        return False
    created = _parse_session_time(session.created_at)
    if created is None:
        return False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (current - created).total_seconds() > max_age_seconds


def mark_stale_running_sessions(
    *,
    now: datetime | None = None,
    max_age_seconds: int = STALE_RUNNING_AFTER_SECONDS,
) -> list[ResearchSession]:
    """Mark stale running sessions as interrupted and return the updated sessions."""
    marked: list[ResearchSession] = []
    for session in list_sessions(status_filter="running"):
        if not is_stale_running_session(session, now=now, max_age_seconds=max_age_seconds):
            continue
        marked.append(
            update_session(
                session.id,
                status="error",
                error="Marked interrupted after the app found a stale running session.",
            )
        )
    return marked


def _is_canonical_session_dir(session: ResearchSession) -> bool:
    """True when meta lives in a folder named after the session id (not latest/ mirror)."""
    try:
        return session.root.name == session.id
    except (AttributeError, TypeError):
        return False


def _dedupe_sessions_by_id(sessions: list[ResearchSession]) -> list[ResearchSession]:
    """Keep one entry per session id; prefer the canonical session folder over mirrors."""
    by_id: dict[str, ResearchSession] = {}
    for session in sessions:
        existing = by_id.get(session.id)
        if existing is None:
            by_id[session.id] = session
            continue
        if _is_canonical_session_dir(session) and not _is_canonical_session_dir(existing):
            by_id[session.id] = session
    return list(by_id.values())


def list_unreadable_session_meta() -> list[Path]:
    """Return session meta files that cannot be parsed into session records."""
    if not RESEARCH_DIR.exists():
        return []
    unreadable: list[Path] = []
    for entry in RESEARCH_DIR.iterdir():
        if not entry.is_dir() or entry.name in SESSION_LIST_SKIP_DIRS:
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            ResearchSession.from_meta(data)
        except (json.JSONDecodeError, KeyError, OSError):
            unreadable.append(meta_path)
    return unreadable


def list_sessions(
    *,
    search: str = "",
    status_filter: str = "all",
    field_filter: str = "all",
    deliverable_filter: str = "all",
    tag_filter: str = "",
) -> list[ResearchSession]:
    """Return sessions pinned-first, then newest-first."""
    if not RESEARCH_DIR.exists():
        return []

    sessions: list[ResearchSession] = []
    for entry in RESEARCH_DIR.iterdir():
        if not entry.is_dir() or entry.name in SESSION_LIST_SKIP_DIRS:
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            sessions.append(ResearchSession.from_meta(data))
        except (json.JSONDecodeError, KeyError, OSError):
            continue

    sessions = _dedupe_sessions_by_id(sessions)

    query = search.strip().lower()
    if query:
        sessions = [
            s
            for s in sessions
            if query in s.display_title().lower()
            or query in s.topic.lower()
            or query in s.field.lower()
            or any(query in tag.lower() for tag in s.tags)
        ]

    if status_filter and status_filter != "all":
        sessions = [s for s in sessions if s.status == status_filter]

    if field_filter and field_filter != "all":
        sessions = [s for s in sessions if s.field.lower() == field_filter.lower()]

    if deliverable_filter and deliverable_filter != "all":
        sessions = [
            s for s in sessions if deliverable_filter.lower() in [d.lower() for d in s.deliverables]
        ]

    tag_query = tag_filter.strip().lower()
    if tag_query:
        sessions = [s for s in sessions if any(tag_query in tag.lower() for tag in s.tags)]

    sessions.sort(key=lambda s: s.created_at, reverse=True)
    sessions.sort(key=lambda s: s.pinned, reverse=True)
    return sessions


def find_referencing_sessions(session_id: str) -> list[ResearchSession]:
    refs: list[ResearchSession] = []
    for session in list_sessions():
        if session.parent_session_id == session_id or session_id in session.linked_sessions:
            refs.append(session)
    return refs


def list_session_files(session: ResearchSession, subdir: str) -> list[Path]:
    return _session_store().list_files(session.id, subdir)


def collect_session_artifacts(session: ResearchSession) -> list[str]:
    artifacts: list[str] = []
    for subdir in SESSION_SUBDIRS:
        for path in list_session_files(session, subdir):
            artifacts.append(str(path.relative_to(PROJECT_ROOT)))
    completion = session.root / "completion.json"
    if completion.exists():
        artifacts.append(str(completion.relative_to(PROJECT_ROOT)))
    for extra in ("sources.json", "corpus_index.json"):
        path = session.root / extra
        if path.exists():
            artifacts.append(str(path.relative_to(PROJECT_ROOT)))
    summaries = session.root / "Papers" / "summaries"
    if summaries.exists():
        for path in summaries.glob("*.md"):
            artifacts.append(str(path.relative_to(PROJECT_ROOT)))
    return artifacts


def load_turns(session_id: str) -> list[SessionTurn]:
    raw = _session_store().load_turns(session_id)
    return [SessionTurn.from_dict(item) for item in raw if isinstance(item, dict)]


def save_turns(session_id: str, turns: list[SessionTurn]) -> None:
    _session_store().save_turns(session_id, [turn.to_dict() for turn in turns])


def append_turn(session_id: str, turn: SessionTurn) -> None:
    _session_store().append_turn(session_id, turn.to_dict())


def load_activity(session_id: str) -> list[str]:
    return _session_store().load_activity(session_id)


def save_activity(session_id: str, entries: list[str]) -> None:
    _session_store().save_activity(session_id, entries)


def append_activity(session_id: str, entry: str) -> None:
    _session_store().append_activity(session_id, entry)


def _truncate(text: str | None, limit: int = MAX_CONTEXT_ANSWER_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[... truncated {len(text) - limit} chars ...]"


def get_session_context_bundle(
    session_ids: list[str],
    *,
    max_answer_chars: int = MAX_CONTEXT_ANSWER_CHARS,
) -> str:
    """Build prior-research context text for linked sessions."""
    if not session_ids:
        return ""

    sections: list[str] = ["## Prior research context"]
    for session_id in session_ids[:MAX_LINKED_SESSIONS]:
        try:
            session = load_session(session_id)
        except FileNotFoundError:
            sections.append(f"\n### Missing session: {session_id}")
            continue

        sections.append(f"\n### Prior session: {session.display_title()}")
        sections.append(f"- Session ID: {session.id}")
        sections.append(f"- Field: {session.field}")
        sections.append(f"- Status: {session.status}")
        sections.append(f"- Deliverables: {', '.join(session.deliverables)}")

        if session.answer:
            sections.append("\n**Prior answer:**")
            sections.append(_truncate(session.answer, max_answer_chars))

        turns = load_turns(session.id)
        if turns:
            sections.append("\n**Turn history:**")
            for index, turn in enumerate(turns, start=1):
                sections.append(f"- Turn {index}: {turn.prompt[:200]}")
                if turn.answer:
                    sections.append(_truncate(turn.answer, 800))

        completion_path = session.root / "completion.json"
        if completion_path.exists():
            try:
                completion = json.loads(completion_path.read_text(encoding="utf-8"))
                if completion.get("summary"):
                    sections.append(f"\n**Completion summary:** {completion['summary']}")
                assumptions = completion.get("assumptions") or []
                if assumptions:
                    sections.append("**Assumptions:** " + "; ".join(str(a) for a in assumptions))
            except json.JSONDecodeError:
                pass

        artifacts = collect_session_artifacts(session)
        if artifacts:
            sections.append("\n**Artifacts (reference, do not duplicate unless requested):**")
            for path in artifacts[:20]:
                sections.append(f"- {path}")

    sections.append(
        "\nBuild on prior findings; do not repeat verbatim. "
        "Cite which prior session informed each claim."
    )
    return "\n".join(sections)


def export_session_zip(session_id: str) -> bytes:
    """Zip all session files for download."""
    return _session_store().export_zip(session_id)


def load_completion(session: ResearchSession | str) -> dict[str, Any] | None:
    """Load completion.json for a session, if present."""
    if isinstance(session, str):
        session = load_session(session)
    path = session.root / "completion.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def publish_session_to_latest(session_id: str) -> Path:
    """Copy key session artifacts to docs/Research/latest/ for quick access."""
    import shutil

    session = load_session(session_id)
    latest_root = ensure_dir(RESEARCH_DIR / "latest")
    for child in latest_root.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    meta_dst = latest_root / "meta.json"
    meta_dst.write_text(
        json.dumps({**session.to_meta(), "source_session_id": session_id}, indent=2),
        encoding="utf-8",
    )

    for name in ("completion.json",):
        src = session.root / name
        if src.exists():
            shutil.copy2(src, latest_root / name)

    for subdir in SESSION_SUBDIRS:
        src_dir = session.root / subdir
        if not src_dir.exists():
            continue
        dst_dir = ensure_dir(latest_root / subdir)
        for path in src_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, dst_dir / path.name)

    if session.answer:
        (latest_root / "answer.md").write_text(session.answer, encoding="utf-8")

    return latest_root


def mission_dict_from_session(session: ResearchSession) -> dict[str, Any]:
    """Build mission JSON dict from a stored session (for retry/duplicate)."""
    objectives = session.objectives or [f"Research and synthesize findings on: {session.topic}"]
    payload: dict[str, Any] = {
        "topic": session.topic,
        "field": session.field,
        "objectives": objectives,
        "deliverables": session.deliverables,
        "audience": session.audience,
        "depth": session.depth,
    }
    if session.scope:
        payload["scope"] = session.scope
    if session.constraints:
        payload["constraints"] = session.constraints
    if session.success_criteria:
        payload["success_criteria"] = session.success_criteria
    return payload
