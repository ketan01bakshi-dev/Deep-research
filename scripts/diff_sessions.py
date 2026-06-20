"""Compare two research sessions (topic, deliverables, answer preview)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.common import bootstrap_env

bootstrap_env()

from deep_research.session_context import collect_session_artifacts, load_session


def diff_sessions(session_a: str, session_b: str) -> str:
    a = load_session(session_a)
    b = load_session(session_b)
    lines = [
        f"Session A: {a.display_title()} ({a.id})",
        f"Session B: {b.display_title()} ({b.id})",
        "",
        f"Field: {a.field} → {b.field}",
        f"Deliverables: {', '.join(a.deliverables)} → {', '.join(b.deliverables)}",
        f"Status: {a.status} → {b.status}",
        "",
        "Artifacts A:",
        *[f"  - {p}" for p in collect_session_artifacts(a)[:15]],
        "Artifacts B:",
        *[f"  - {p}" for p in collect_session_artifacts(b)[:15]],
    ]
    if a.answer and b.answer:
        lines.extend(
            [
                "",
                f"Answer A ({len(a.answer)} chars): {a.answer[:400]}…",
                f"Answer B ({len(b.answer)} chars): {b.answer[:400]}…",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff two research sessions.")
    parser.add_argument("session_a")
    parser.add_argument("session_b")
    args = parser.parse_args()
    try:
        print(diff_sessions(args.session_a, args.session_b))
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
