#!/usr/bin/env python3
"""Run the autonomous deep-research agent with a structured mission."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from agent_core import load_agent_env

from deep_research.autonomous import run_autonomous_mission
from deep_research.autonomous_examples import (
    AUTONOMOUS_MISSION_EXAMPLES,
    get_autonomous_example,
)
from deep_research.autonomous_mission import mission_from_json
from cursor_agent_core.runtime.console import configure_stdio
from deep_research.display import default_activity_handler, format_autonomous_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Autonomous research agent. Provide a rich mission at step 1; "
            "the agent works through deliverables without mid-run questions."
        ),
    )
    parser.add_argument(
        "--example",
        choices=[example.id for example in AUTONOMOUS_MISSION_EXAMPLES],
        default="protein_digestion_full",
        help="Predefined mission example (default: protein_digestion_full)",
    )
    parser.add_argument(
        "--mission-file",
        help="Path to mission JSON file (overrides --example)",
    )
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List autonomous mission examples and exit",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("RESEARCH_MODEL"),
        help="Cursor model id (default: composer-2.5 or RESEARCH_MODEL env)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress live activity on stderr",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Auto-retries when artifact deliverables are missing (default: 1)",
    )
    return parser.parse_args()


def list_examples() -> None:
    print("Autonomous mission examples:\n")
    for example in AUTONOMOUS_MISSION_EXAMPLES:
        deliverables = example.mission.normalized_deliverables()
        print(f"  {example.id}")
        print(f"    {example.title}")
        print(f"    Topic: {example.mission.topic}")
        print(f"    Deliverables: {', '.join(deliverables) or '(none — triggers clarification)'}")
        print()


def main() -> int:
    configure_stdio()
    load_agent_env(Path(__file__).resolve().parent)
    args = parse_args()

    if args.list_examples:
        list_examples()
        return 0

    if not os.environ.get("CURSOR_API_KEY"):
        print(
            "CURSOR_API_KEY is not set. Copy .env.example to .env and add your key.",
            file=sys.stderr,
        )
        return 1

    if args.mission_file:
        mission = mission_from_json(args.mission_file)
        title = mission.topic
    else:
        example = get_autonomous_example(args.example)
        mission = example.mission
        title = example.title

    print(f"Autonomous mission: {title}\n", file=sys.stderr)
    print(f"Topic: {mission.topic}", file=sys.stderr)
    print(f"Field: {mission.field}", file=sys.stderr)
    print(f"Deliverables: {', '.join(mission.normalized_deliverables()) or '(unspecified)'}", file=sys.stderr)
    print("-" * 72, file=sys.stderr)

    result = run_autonomous_mission(
        mission,
        model=args.model,
        max_completion_retries=args.max_retries,
        on_message=None if args.quiet else default_activity_handler,
    )

    if result.answer:
        print(result.answer)
    elif result.error:
        print(result.error, file=sys.stderr)

    print(format_autonomous_summary(result), file=sys.stderr)

    if result.clarification_needed:
        return 0
    return 0 if not result.is_error else 2


if __name__ == "__main__":
    raise SystemExit(main())
