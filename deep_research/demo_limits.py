"""Session cleanup and demo limit helpers."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from deep_research.demo_config import demo_session_ttl_hours, is_public_demo
from deep_research.session_context import SESSION_LIST_SKIP_DIRS, list_sessions


def _parse_created_at(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def purge_expired_demo_sessions(*, now: datetime | None = None) -> list[str]:
    """Delete session folders older than demo TTL. Returns deleted session IDs."""
    if not is_public_demo():
        return []

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(hours=demo_session_ttl_hours())
    deleted: list[str] = []

    for session in list_sessions():
        if session.id in SESSION_LIST_SKIP_DIRS:
            continue
        created = _parse_created_at(session.created_at)
        if created is None or created > cutoff:
            continue
        root = session.root
        if not root.is_dir():
            continue
        shutil.rmtree(root, ignore_errors=True)
        deleted.append(session.id)
    return deleted
