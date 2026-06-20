"""Public demo mode configuration and Streamlit secrets bridge."""

from __future__ import annotations

import os
from pathlib import Path

from agent_core.quota import DailyQuota

DEFAULT_MAX_DEMO_MISSIONS_PER_DAY = 10
DEFAULT_DEMO_SESSION_TTL_HOURS = 72
DEMO_USAGE_FILE = Path("profile/.demo_mission_usage.json")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def apply_streamlit_secrets() -> None:
    """Copy Streamlit Cloud secrets into os.environ when running on Streamlit."""
    try:
        import streamlit as st
    except ImportError:
        return
    try:
        secrets = dict(st.secrets)
    except Exception:
        return
    for key, value in secrets.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(str(key), str(value))


def is_public_demo() -> bool:
    return _truthy(os.environ.get("PUBLIC_DEMO"))


def demo_password() -> str | None:
    value = os.environ.get("DEMO_PASSWORD", "").strip()
    return value or None


def max_demo_missions_per_day() -> int:
    raw = os.environ.get("MAX_DEMO_MISSIONS_PER_DAY", "").strip()
    if not raw:
        return DEFAULT_MAX_DEMO_MISSIONS_PER_DAY
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_DEMO_MISSIONS_PER_DAY


def demo_session_ttl_hours() -> int:
    raw = os.environ.get("DEMO_SESSION_TTL_HOURS", "").strip()
    if not raw:
        return DEFAULT_DEMO_SESSION_TTL_HOURS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_DEMO_SESSION_TTL_HOURS


def allowed_deliverables() -> frozenset[str]:
    if not is_public_demo():
        return frozenset(
            {"answer", "report", "mindmap", "slides", "papers", "paper_summary"}
        )
    raw = os.environ.get("DEMO_ALLOWED_DELIVERABLES", "answer").strip()
    return frozenset(part.strip() for part in raw.split(",") if part.strip()) or frozenset(
        {"answer"}
    )


def pipeline_enabled_in_demo() -> bool:
    if not is_public_demo():
        return True
    return _truthy(os.environ.get("DEMO_ALLOW_PIPELINE"))


def load_demo_mission_quota() -> DailyQuota:
    return DailyQuota.load(DEMO_USAGE_FILE)


def demo_missions_remaining() -> int:
    quota = load_demo_mission_quota()
    return quota.remaining(max_demo_missions_per_day())


def record_demo_mission_start() -> int:
    quota = load_demo_mission_quota()
    quota.reset_if_new_day()
    count = quota.record()
    quota.save(DEMO_USAGE_FILE)
    return count


def can_start_demo_mission() -> bool:
    if not is_public_demo():
        return True
    return demo_missions_remaining() > 0
