#!/usr/bin/env python3
"""
Demonstrate phase-2 conversational research with scripted multi-turn examples.

Each example runs every turn in a single agent so follow-ups reference prior analysis.
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from cursor_agent_core.runtime.console import configure_stdio
from deep_research.conversation import ConversationalResearchAgent
from deep_research.conversation_examples import CONVERSATION_EXAMPLES, ConversationExample
from deep_research.display import format_result_summary


def run_conversation_example(example: ConversationExample) -> bool:
    print(f"\n{'#' * 72}")
    print(f"# {example.title} ({example.id})")
    print(f"# {len(example.turns)} turns in one agent session")
    print(f"{'#' * 72}\n", file=sys.stderr)

    with ConversationalResearchAgent() as agent:
        result = agent.run_turns(
            [turn.prompt for turn in example.turns],
            example_id=example.id,
            title=example.title,
        )

        for index, turn in enumerate(result.turns, start=1):
            print(f"\n--- Turn {index} ---")
            print(f"Prompt: {turn.question}\n")
            if turn.answer:
                print(turn.answer)
            print(format_result_summary(turn, session_label="Agent"), file=sys.stderr)
            if turn.is_error:
                return False

        if result.session_id:
            print(f"\nAgent ID (for resume): {result.session_id}", file=sys.stderr)

    return True


def main() -> int:
    configure_stdio()
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run conversational health research demos")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all conversational examples (separate agents)",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        choices=[example.id for example in CONVERSATION_EXAMPLES],
        help="Run specific conversation example ids",
    )
    args = parser.parse_args()

    if not os.environ.get("CURSOR_API_KEY"):
        print("Set CURSOR_API_KEY in .env before running demos.", file=sys.stderr)
        return 1

    if args.all:
        examples = list(CONVERSATION_EXAMPLES)
    elif args.ids:
        examples = [
            next(e for e in CONVERSATION_EXAMPLES if e.id == example_id)
            for example_id in args.ids
        ]
    else:
        examples = [
            next(e for e in CONVERSATION_EXAMPLES if e.id == "protein_digestion_deep_dive")
        ]

    ok = True
    for example in examples:
        if not run_conversation_example(example):
            ok = False
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
