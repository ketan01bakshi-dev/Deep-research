"""Schedule autonomous missions (Windows Task Scheduler / manual cron)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.common import bootstrap_env

bootstrap_env()

from deep_research.autonomous import run_autonomous_mission
from deep_research.autonomous_mission import mission_from_dict, mission_from_json
from deep_research.pipeline import run_pipeline_mission
from deep_research.display import format_autonomous_summary
from deep_research.session_context import mark_stale_running_sessions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a scheduled Deep Research mission.")
    parser.add_argument("--mission-file", required=True, help="Path to mission JSON file")
    parser.add_argument("--pipeline", action="store_true", help="Use multi-agent pipeline")
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--compare-session", help="Prior session ID for diff note in stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.mission_file)
    if not path.exists():
        print(f"Mission file not found: {path}", file=sys.stderr)
        return 1

    mission = mission_from_json(path)
    mark_stale_running_sessions()
    runner = run_pipeline_mission if args.pipeline else run_autonomous_mission
    result = runner(mission, max_completion_retries=args.max_retries)

    print(format_autonomous_summary(result))
    if args.compare_session and result.session_id:
        from scripts.diff_sessions import diff_sessions

        print("\n--- Diff vs prior session ---")
        print(diff_sessions(args.compare_session, result.session_id))

    return 0 if not result.is_error else 2


if __name__ == "__main__":
    raise SystemExit(main())
