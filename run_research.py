#!/usr/bin/env python3
"""Run the phase-1 stateless deep-research agent with health demo queries."""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from deep_research.agent import (
    default_activity_handler,
    format_result_summary,
    run_research,
)
from cursor_agent_core.runtime.console import configure_stdio
from deep_research.examples import HEALTH_RESEARCH_EXAMPLES, get_example


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stateless health research agent (Cursor SDK). "
            "Each query is independent — no memory between runs."
        ),
    )
    parser.add_argument(
        "--example",
        choices=[example.id for example in HEALTH_RESEARCH_EXAMPLES],
        default="protein_digestion",
        help="Predefined health research demo (default: protein_digestion)",
    )
    parser.add_argument(
        "--prompt",
        help="Custom research question (overrides --example)",
    )
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List available health research demos and exit",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("RESEARCH_MODEL"),
        help="Cursor model id (default: composer-2.5 or RESEARCH_MODEL env)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress live activity on stderr; print only the final answer",
    )
    return parser.parse_args()


def list_examples() -> None:
    print("Available health research examples:\n")
    for example in HEALTH_RESEARCH_EXAMPLES:
        print(f"  {example.id}")
        print(f"    {example.title}")
        print(f"    {example.prompt[:100]}...")
        print()


def main() -> int:
    configure_stdio()
    load_dotenv()
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

    if args.prompt:
        question = args.prompt
        title = "Custom query"
    else:
        example = get_example(args.example)
        question = example.prompt
        title = example.title

    print(f"Research: {title}\n", file=sys.stderr)
    print(f"Question:\n{question}\n", file=sys.stderr)
    print("-" * 72, file=sys.stderr)

    result = run_research(
        question,
        model=args.model,
        on_message=None if args.quiet else default_activity_handler,
    )

    if result.answer:
        print(result.answer)
    else:
        print(result.error or "No answer returned.", file=sys.stderr)
        return 2

    print(format_result_summary(result), file=sys.stderr)
    return 0 if not result.is_error else 2


if __name__ == "__main__":
    raise SystemExit(main())
