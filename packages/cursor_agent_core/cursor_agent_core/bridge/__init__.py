"""Cursor SDK bridge lifecycle and Windows compatibility."""

from cursor_agent_core.bridge.client import cursor_client
from cursor_agent_core.bridge.windows_compat import apply_windows_compat

__all__ = ["apply_windows_compat", "cursor_client"]
