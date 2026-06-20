"""Thin adapter between agent code and the Cursor SDK."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from cursor_sdk import Agent, CursorAgentError

from cursor_agent_core.bridge.client import cursor_client
from cursor_agent_core.runtime.options import build_agent_options
from cursor_agent_core.runtime.types import AgentResult

MessageHandler = Callable[[Any], None]


def prefix_prompt(prompt: str, system_prompt: str) -> str:
    """Embed system instructions because Cursor AgentOptions has no system_prompt."""
    return f"{system_prompt.strip()}\n\n---\n\nUser request:\n{prompt}"


def handle_stream_message(message: Any, on_message: MessageHandler | None) -> None:
    """Print Cursor SDK stream events and forward to optional handler."""
    if on_message is not None:
        on_message(message)

    msg_type = getattr(message, "type", None)
    if msg_type == "assistant":
        content = getattr(getattr(message, "message", None), "content", None) or []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", "")
                if text.strip():
                    print(text, end="", flush=True, file=sys.stderr)
    elif msg_type == "tool_call":
        name = getattr(message, "name", "tool")
        status = getattr(message, "status", "")
        if status == "running":
            print(f"\n[tool] {name}", file=sys.stderr, flush=True)
    elif msg_type == "status":
        status = getattr(message, "status", "")
        detail = getattr(message, "message", "")
        if status == "error" or "error" in str(detail).lower():
            print(f"\n[error] {detail or status}", file=sys.stderr, flush=True)


def count_tool_turns(messages: list[Any]) -> int:
    """Approximate agentic turns from completed tool calls."""
    completed = sum(
        1
        for message in messages
        if getattr(message, "type", None) == "tool_call"
        and getattr(message, "status", None) == "completed"
    )
    return max(completed, 1)


def run_to_result(
    question: str,
    *,
    agent_id: str | None,
    run_result: Any,
    messages: list[Any],
    error: str | None = None,
) -> AgentResult:
    """Map a Cursor RunResult to AgentResult."""
    status = getattr(run_result, "status", "error")
    is_error = status != "finished"
    subtype = "success" if status == "finished" else status

    return AgentResult(
        question=question,
        answer=getattr(run_result, "result", None) or None,
        session_id=agent_id,
        num_turns=count_tool_turns(messages),
        total_cost_usd=None,
        is_error=is_error,
        subtype=subtype,
        error=error,
        messages=messages,
    )


def error_result(
    question: str,
    *,
    error: str,
    agent_id: str | None = None,
    messages: list[Any] | None = None,
) -> AgentResult:
    return AgentResult(
        question=question,
        answer=None,
        session_id=agent_id,
        num_turns=0,
        total_cost_usd=None,
        is_error=True,
        subtype="error_during_execution",
        error=error,
        messages=messages or [],
    )


def consume_run(run: Any, on_message: MessageHandler | None) -> list[Any]:
    """Drain run.messages() once and optionally print activity."""
    messages: list[Any] = []
    for message in run.messages():
        messages.append(message)
        handle_stream_message(message, on_message)
    return messages


def run_stateless_prompt(
    prompt: str,
    *,
    system_prompt: str,
    project_root: str,
    model: str | None = None,
    api_key: str | None = None,
    custom_tools: dict | None = None,
    default_model_env: str = "AGENT_MODEL",
    fallback_model: str = "composer-2.5",
    on_message: MessageHandler | None = None,
) -> AgentResult:
    """One-shot agent run via Agent.prompt()."""
    _ = on_message
    full_prompt = prefix_prompt(prompt, system_prompt)
    options = build_agent_options(
        project_root=project_root,
        custom_tools=custom_tools,
        model=model,
        api_key=api_key,
        default_model_env=default_model_env,
        fallback_model=fallback_model,
    )

    try:
        with cursor_client(workspace=project_root) as client:
            result = Agent.prompt(full_prompt, options, client=client)
    except CursorAgentError as exc:
        return error_result(prompt, error=str(exc.message))
    except OSError as exc:
        return error_result(prompt, error=f"Bridge launch failed: {exc}")
    except Exception as exc:
        return error_result(prompt, error=str(exc))

    if result.status != "finished":
        return AgentResult(
            question=prompt,
            answer=result.result,
            session_id=None,
            num_turns=0,
            total_cost_usd=None,
            is_error=True,
            subtype=result.status,
            error=result.result or "Run failed",
            messages=[],
        )

    return AgentResult(
        question=prompt,
        answer=result.result,
        session_id=None,
        num_turns=1,
        total_cost_usd=None,
        is_error=False,
        subtype="success",
        messages=[],
    )


def run_agent_turn(
    agent: Any,
    prompt: str,
    *,
    on_message: MessageHandler | None = None,
    prefix_system: str | None = None,
) -> AgentResult:
    """Send one prompt on an existing agent and return AgentResult."""
    message = prefix_prompt(prompt, prefix_system) if prefix_system else prompt
    messages: list[Any] = []

    try:
        run = agent.send(message)
        messages = consume_run(run, on_message)
        run_result = run.wait()
    except CursorAgentError as exc:
        return error_result(
            prompt,
            error=str(exc.message),
            agent_id=getattr(agent, "agent_id", None),
            messages=messages,
        )

    return run_to_result(
        prompt,
        agent_id=getattr(agent, "agent_id", None),
        run_result=run_result,
        messages=messages,
    )


def run_resume_turn(
    agent_id: str,
    prompt: str,
    *,
    project_root: str,
    model: str | None = None,
    api_key: str | None = None,
    custom_tools: dict | None = None,
    default_model_env: str = "AGENT_MODEL",
    fallback_model: str = "composer-2.5",
    on_message: MessageHandler | None = None,
    prefix_system: str | None = None,
) -> AgentResult:
    """Resume a persisted agent by ID and send one follow-up."""
    options = build_agent_options(
        project_root=project_root,
        custom_tools=custom_tools,
        model=model,
        api_key=api_key,
        default_model_env=default_model_env,
        fallback_model=fallback_model,
    )

    try:
        with cursor_client(workspace=project_root) as client:
            with Agent.resume(agent_id, options, client=client) as agent:
                return run_agent_turn(
                    agent,
                    prompt,
                    on_message=on_message,
                    prefix_system=prefix_system,
                )
    except CursorAgentError as exc:
        return error_result(prompt, error=str(exc.message), agent_id=agent_id)
    except OSError as exc:
        return error_result(prompt, error=f"Bridge launch failed: {exc}", agent_id=agent_id)
    except Exception as exc:
        return error_result(prompt, error=str(exc), agent_id=agent_id)
