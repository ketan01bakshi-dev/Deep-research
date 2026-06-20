"""Shared CursorClient lifecycle."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from cursor_sdk import CursorClient

from cursor_agent_core.bridge.windows_compat import apply_windows_compat


@contextmanager
def cursor_client(*, workspace: str) -> Iterator[CursorClient]:
    """Launch the SDK bridge against the given workspace directory."""
    apply_windows_compat()
    with CursorClient.launch_bridge(workspace=workspace) as client:
        yield client
