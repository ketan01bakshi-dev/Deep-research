"""Session browser widget key helpers."""

from __future__ import annotations


def session_row_widget_keys(session_id: str, row_idx: int) -> dict[str, str]:
    """Stable unique Streamlit keys for one session row."""
    suffix = f"{session_id}_{row_idx}"
    return {
        "bulk": f"bulk_{suffix}",
        "open": f"open_{suffix}",
        "pin": f"pin_{suffix}",
        "del": f"del_{suffix}",
    }


def assert_unique_widget_keys(session_ids: list[str]) -> None:
    """Raise if keys would collide when rendered with enumerate indices."""
    keys: list[str] = []
    for row_idx, session_id in enumerate(session_ids):
        keys.extend(session_row_widget_keys(session_id, row_idx).values())
    assert len(keys) == len(set(keys)), f"duplicate widget keys: {keys}"
