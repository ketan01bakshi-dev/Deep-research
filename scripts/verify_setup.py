#!/usr/bin/env python3
"""Verify a fresh clone can import core modules and find required files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    check((ROOT / "app.py").exists(), "app.py missing")
    check((ROOT / "requirements.txt").exists(), "requirements.txt missing")
    check((ROOT / "packages" / "agent_core").is_dir(), "packages/agent_core missing")
    check((ROOT / "packages" / "cursor_agent_core").is_dir(), "packages/cursor_agent_core missing")
    check((ROOT / ".env.example").exists(), ".env.example missing")
    check((ROOT / "LICENSE").exists(), "LICENSE missing")

    try:
        import deep_research  # noqa: F401
    except ImportError as exc:
        errors.append(f"deep_research import failed: {exc}")

    try:
        from deep_research.demo_config import is_public_demo

        check(is_public_demo() is False or True, "")  # smoke call
    except ImportError as exc:
        errors.append(f"demo_config import failed: {exc}")

    if errors:
        print("Setup verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Setup verification OK")
    print(f"  Project root: {ROOT}")
    print("  Next: copy .env.example to .env, add API keys, run run_app.cmd")
    return 0


if __name__ == "__main__":
    sys.exit(main())
