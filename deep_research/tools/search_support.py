"""Tavily search caching and daily quota tracking."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_core.io import load_json, save_json
from agent_core.quota import DailyQuota

from deep_research.session_context import get_active_session
from deep_research.tools.paths import PROJECT_ROOT

CACHE_DIR = PROJECT_ROOT / "profile" / ".tavily_cache"
QUOTA_PATH = PROJECT_ROOT / "profile" / ".tavily_usage.json"
DEFAULT_DAILY_LIMIT = 100


def _cache_key(query: str, source_mode: str, max_results: int, time_range: str) -> str:
    raw = f"{query}|{source_mode}|{max_results}|{time_range}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _session_cache_dir() -> Path:
    session = get_active_session()
    if session:
        return session.root / ".cache" / "tavily"
    return CACHE_DIR


def load_cached_search(
    query: str,
    *,
    source_mode: str,
    max_results: int,
    time_range: str,
) -> dict | None:
    """Return cached Tavily payload if present for this query fingerprint."""
    cache_dir = _session_cache_dir()
    path = cache_dir / f"{_cache_key(query, source_mode, max_results, time_range)}.json"
    data = load_json(path, default=None)
    return data if isinstance(data, dict) else None


def save_cached_search(
    query: str,
    *,
    source_mode: str,
    max_results: int,
    time_range: str,
    payload: dict,
) -> None:
    cache_dir = _session_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{_cache_key(query, source_mode, max_results, time_range)}.json"
    save_json(path, payload)


def check_tavily_quota(*, limit: int = DEFAULT_DAILY_LIMIT) -> tuple[bool, int]:
    """Return (allowed, remaining) for today's Tavily calls."""
    quota = DailyQuota.load(QUOTA_PATH)
    remaining = quota.remaining(limit)
    return remaining > 0, remaining


def record_tavily_call() -> int:
    """Increment today's Tavily usage counter."""
    quota = DailyQuota.load(QUOTA_PATH)
    count = quota.record()
    quota.save(QUOTA_PATH)
    return count


def extract_citations_from_results(results: list[dict]) -> list[dict]:
    """Normalize search hits into citation records."""
    citations: list[dict] = []
    seen: set[str] = set()
    for item in results:
        url = str(item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        citations.append(
            {
                "title": str(item.get("title") or url),
                "url": url,
                "source_type": item.get("source_type") or "article",
                "snippet": (item.get("snippet") or "")[:300],
                "published_date": item.get("published_date"),
            }
        )
    return citations


def save_sources_artifact(citations: list[dict]) -> str | None:
    """Write sources.json under the active session root."""
    session = get_active_session()
    if not session or not citations:
        return None
    path = session.root / "sources.json"
    save_json(path, {"sources": citations, "count": len(citations)})
    return str(path.relative_to(PROJECT_ROOT))
