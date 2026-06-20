#!/usr/bin/env python3
"""
Demonstrate the stateless research agent with built-in health examples.

Phase 1 uses Agent.prompt() — each example runs in isolation with no shared memory.
Run the protein digestion demo by default; pass --all to run every example.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from deep_research.agent import format_result_summary, run_research
from cursor_agent_core.runtime.console import configure_stdio
from deep_research.examples import HEALTH_RESEARCH_EXAMPLES, ResearchExample


def run_example(example: ResearchExample) -> bool:
    """Run one demo example and print its result."""
    print(f"\n{'#' * 72}")
    print(f"# {example.title} ({example.id})")
    print(f"{'#' * 72}\n")
    print(f"Prompt:\n{example.prompt}\n")
    print("-" * 72)

    result = run_research(example.prompt)
    if result.answer:
        print(result.answer)
    print(format_result_summary(result), file=sys.stderr)
    return not result.is_error


def main() -> int:
    configure_stdio()
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run health research demos")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all health examples (each is a separate stateless query)",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        choices=[example.id for example in HEALTH_RESEARCH_EXAMPLES],
        help="Run specific example ids",
    )
    args = parser.parse_args()

    if not os.environ.get("CURSOR_API_KEY"):
        print("Set CURSOR_API_KEY in .env before running demos.", file=sys.stderr)
        return 1

    if args.all:
        examples = list(HEALTH_RESEARCH_EXAMPLES)
    elif args.ids:
        examples = [next(e for e in HEALTH_RESEARCH_EXAMPLES if e.id == i) for i in args.ids]
    else:
        examples = [next(e for e in HEALTH_RESEARCH_EXAMPLES if e.id == "protein_digestion")]

    ok = True
    for example in examples:
        if not run_example(example):
            ok = False
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
