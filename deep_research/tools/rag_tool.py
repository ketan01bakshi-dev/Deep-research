"""RAG-lite custom tool for grounded session queries."""

from __future__ import annotations

import json
from typing import Any

from cursor_sdk import CustomTool, CustomToolContext

from deep_research.rag import build_session_corpus, format_corpus_context, query_session_corpus
from deep_research.session_context import get_active_session


def query_session_corpus_tool(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    session = get_active_session()
    if session is None:
        raise ValueError("No active research session")

    question = str(args.get("question") or "").strip()
    if not question:
        raise ValueError("question is required")

    top_k = int(args.get("top_k") or 5)
    top_k = max(1, min(top_k, 10))

    if args.get("rebuild_index", False):
        build_session_corpus(session.id)

    hits = query_session_corpus(session.id, question, top_k=top_k)
    return json.dumps(
        {
            "question": question,
            "hit_count": len(hits),
            "context": format_corpus_context(hits),
            "hits": hits,
        },
        indent=2,
    )


QUERY_SESSION_CORPUS_TOOL = CustomTool(
    execute=query_session_corpus_tool,
    description=(
        "Search indexed text from this session's downloaded PDFs and reports. "
        "Use for follow-up questions grounded in session sources. "
        "Set rebuild_index=true after new PDFs are downloaded."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question to answer from session corpus."},
            "top_k": {"type": "integer", "description": "Number of chunks to return (1-10)."},
            "rebuild_index": {
                "type": "boolean",
                "description": "Rebuild corpus index before querying.",
            },
        },
        "required": ["question"],
    },
)
