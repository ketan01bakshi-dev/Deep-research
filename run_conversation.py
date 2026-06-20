#!/usr/bin/env python3
"""Run multi-turn conversational health research (phase 2)."""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from cursor_agent_core.runtime.console import configure_stdio
from deep_research.conversation import ConversationalResearchAgent, resume_research
from deep_research.conversation_examples import CONVERSATION_EXAMPLES, get_conversation_example
from deep_research.display import default_activity_handler, format_result_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Conversational health research agent with session memory (Cursor SDK). "
            "Follow-up questions build on prior turns in the same agent."
        ),
    )
    parser.add_argument(
        "--example",
        choices=[example.id for example in CONVERSATION_EXAMPLES],
        default="protein_digestion_deep_dive",
        help="Scripted multi-turn demo (default: protein_digestion_deep_dive)",
    )
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List conversational demos and exit",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive REPL — multiple prompts in one session",
    )
    parser.add_argument(
        "--resume",
        metavar="AGENT_ID",
        help="Resume a persisted agent and send one follow-up (--prompt required)",
    )
    parser.add_argument(
        "--prompt",
        help="Custom follow-up when using --resume, or first message in --interactive",
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
    return parser.parse_args()


def list_examples() -> None:
    print("Conversational research examples:\n")
    for example in CONVERSATION_EXAMPLES:
        print(f"  {example.id}")
        print(f"    {example.title}")
        for index, turn in enumerate(example.turns, start=1):
            preview = turn.prompt.replace("\n", " ")
            print(f"    Turn {index}: {preview[:90]}...")
        print()


def print_turn(turn_number: int, prompt: str, answer: str | None) -> None:
    print(f"\n--- Turn {turn_number} ---", file=sys.stderr)
    print(f"You: {prompt}\n", file=sys.stderr)
    if answer:
        print(answer)


def run_scripted_example(args: argparse.Namespace) -> int:
    example = get_conversation_example(args.example)
    handler = None if args.quiet else default_activity_handler

    print(f"Conversation: {example.title}\n", file=sys.stderr)

    with ConversationalResearchAgent(
        model=args.model,
        on_message=handler,
    ) as agent:
        result = agent.run_turns(
            [turn.prompt for turn in example.turns],
            example_id=example.id,
            title=example.title,
        )

        for index, turn in enumerate(result.turns, start=1):
            print_turn(index, turn.question, turn.answer)
            print(format_result_summary(turn, session_label="Agent"), file=sys.stderr)

        if result.session_id:
            print(
                f"\nResume later with:\n"
                f"  .venv\\Scripts\\python run_conversation.py "
                f"--resume {result.session_id} --prompt \"Your follow-up\"",
                file=sys.stderr,
            )

    return 0 if not result.is_error else 2


def run_interactive(args: argparse.Namespace) -> int:
    handler = None if args.quiet else default_activity_handler
    turn_number = 0

    with ConversationalResearchAgent(
        model=args.model,
        on_message=handler,
    ) as agent:
        if args.prompt:
            turn_number += 1
            turn = agent.ask(args.prompt)
            print_turn(turn_number, turn.question, turn.answer)
            if turn.is_error:
                return 2

        print(
            "Interactive mode — enter research questions (empty line or Ctrl+C to exit).\n",
            file=sys.stderr,
        )
        while True:
            try:
                prompt = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print(file=sys.stderr)
                break
            if not prompt:
                break
            turn_number += 1
            turn = agent.ask(prompt)
            print()
            print_turn(turn_number, turn.question, turn.answer)
            print(format_result_summary(turn, session_label="Agent"), file=sys.stderr)
            if turn.is_error:
                return 2

        if agent.session_id:
            print(f"\nAgent ID: {agent.session_id}", file=sys.stderr)

    return 0


def run_resume(args: argparse.Namespace) -> int:
    if not args.prompt:
        print("--prompt is required when using --resume", file=sys.stderr)
        return 1

    handler = None if args.quiet else default_activity_handler
    turn = resume_research(
        args.resume,
        args.prompt,
        model=args.model,
        on_message=handler,
    )
    print_turn(1, turn.question, turn.answer)
    print(format_result_summary(turn, session_label="Agent"), file=sys.stderr)
    return 0 if not turn.is_error else 2


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

    if args.resume:
        return run_resume(args)
    if args.interactive:
        return run_interactive(args)
    return run_scripted_example(args)


if __name__ == "__main__":
    raise SystemExit(main())
