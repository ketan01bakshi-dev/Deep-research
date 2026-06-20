"""Windows compatibility patches for cursor-sdk bridge discovery."""

from __future__ import annotations

import sys
import time
from typing import Any

_PATCHED = False


def apply_windows_compat() -> None:
    """
    Patch cursor-sdk bridge discovery on Windows.

    DefaultSelector.select() cannot poll pipe handles on Windows (WinError 10038).
    Replace with a readline polling loop.
    """
    global _PATCHED
    if _PATCHED or sys.platform != "win32":
        _PATCHED = True
        return

    import cursor_sdk._bridge as bridge_mod
    from cursor_sdk.errors import CursorSDKError

    def read_discovery_windows(
        process: Any,
        timeout: float,
    ) -> dict[str, Any]:
        if process.stderr is None:
            raise CursorSDKError("Bridge process stderr is unavailable")

        deadline = time.monotonic() + timeout
        stderr_lines: list[str] = []

        while time.monotonic() < deadline:
            line = process.stderr.readline()
            if line:
                stderr_lines.append(line)
                discovery = bridge_mod.parse_discovery_line(line)
                if discovery is not None:
                    return discovery

            exit_code = process.poll()
            if exit_code is not None:
                raise CursorSDKError(
                    f"Bridge exited before discovery with status {exit_code}: "
                    + "".join(stderr_lines)
                )
            time.sleep(0.05)

        raise CursorSDKError("Timed out waiting for bridge discovery")

    bridge_mod._read_discovery = read_discovery_windows
    _PATCHED = True
