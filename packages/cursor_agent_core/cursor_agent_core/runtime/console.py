"""Windows-friendly stdio configuration."""

from __future__ import annotations

import sys


def configure_stdio() -> None:
    """Use UTF-8 output so answers with arrows/symbols print on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
