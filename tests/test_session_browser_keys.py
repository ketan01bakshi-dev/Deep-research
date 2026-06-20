"""Session browser Streamlit key uniqueness tests."""

from __future__ import annotations

from deep_research.web.session_browser_keys import assert_unique_widget_keys, session_row_widget_keys


def test_session_row_widget_keys_are_unique_per_row():
    keys_a = session_row_widget_keys("session-a", 0)
    keys_b = session_row_widget_keys("session-a", 1)
    assert keys_a["open"] != keys_b["open"]
    assert keys_a["pin"] != keys_b["pin"]


def test_assert_unique_widget_keys_passes_for_distinct_sessions():
    assert_unique_widget_keys(
        [
            "20260613-122129_most-promising-research-for-curing-type-2-diabetes-completely_43cf",
            "20260613-054548_type-2-diabetes-reversal-research_a8e5",
        ]
    )


def test_assert_unique_widget_keys_passes_when_same_id_would_have_collided_before_row_idx():
    """Duplicate session ids at different row indices must still produce unique keys."""
    duplicate_id = "20260613-122129_most-promising-research-for-curing-type-2-diabetes-completely_43cf"
    assert_unique_widget_keys([duplicate_id, duplicate_id])
