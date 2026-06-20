"""Custom CSS for the Deep Research Streamlit app."""

from __future__ import annotations

import streamlit as st


def apply_page_config() -> None:
    st.set_page_config(
        page_title="Deep Research",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f7f8fa 0%, #eef1f5 100%);
        }
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e6ea;
        }
        .dr-card {
            background: #ffffff;
            border: 1px solid #e2e6ea;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }
        .dr-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .dr-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        .dr-session-item {
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.35rem;
            border: 1px solid transparent;
        }
        .dr-session-active {
            background: #eff6ff;
            border-color: #bfdbfe;
        }
        .dr-activity-log {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.8rem;
            background: #0f172a;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            max-height: 220px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .dr-empty {
            color: #64748b;
            font-style: italic;
            padding: 2rem 0;
            text-align: center;
        }
        .dr-badge {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 0.35rem;
        }
        .dr-badge-running { background: #fef3c7; color: #92400e; }
        .dr-badge-completed { background: #dcfce7; color: #166534; }
        .dr-badge-error { background: #fee2e2; color: #991b1b; }
        .dr-badge-pending { background: #e2e8f0; color: #475569; }
        .dr-badge-cancelled { background: #f1f5f9; color: #475569; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    css = {
        "running": "dr-badge-running",
        "completed": "dr-badge-completed",
        "error": "dr-badge-error",
        "pending": "dr-badge-pending",
        "cancelled": "dr-badge-cancelled",
    }.get(status, "dr-badge-pending")
    return f'<span class="dr-badge {css}">{status}</span>'
