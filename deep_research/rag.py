"""Lightweight session corpus index for grounded follow-up queries (RAG-lite)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agent_core.io import load_json, save_json

from deep_research.session_context import ResearchSession, list_session_files, load_session
from deep_research.tools.paths import PROJECT_ROOT

_CHUNK_SIZE = 800
_INDEX_NAME = "corpus_index.json"


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower())}


def _chunk_text(text: str, *, source: str, chunk_size: int = _CHUNK_SIZE) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    words = text.split()
    for index in range(0, len(words), chunk_size // 5):
        segment = " ".join(words[index : index + chunk_size // 5])
        if len(segment.strip()) < 80:
            continue
        chunks.append({"source": source, "text": segment.strip(), "index": len(chunks)})
    return chunks


def _extract_pdf_chunks(pdf_path: Path) -> list[dict[str, Any]]:
    try:
        import fitz
    except ImportError:
        return []
    rel = str(pdf_path.relative_to(PROJECT_ROOT))
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return _chunk_text(text, source=rel)


def build_session_corpus(session_id: str) -> dict[str, Any]:
    """Index PDFs and report markdown for a session."""
    session = load_session(session_id)
    chunks: list[dict[str, Any]] = []

    for pdf in list_session_files(session, "Papers"):
        if pdf.suffix.lower() == ".pdf":
            chunks.extend(_extract_pdf_chunks(pdf))

    for report in list_session_files(session, "Reports"):
        if report.suffix.lower() == ".md":
            rel = str(report.relative_to(PROJECT_ROOT))
            chunks.extend(_chunk_text(report.read_text(encoding="utf-8"), source=rel))

    if session.answer:
        chunks.extend(_chunk_text(session.answer, source="session_answer"))

    index = {
        "session_id": session_id,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    path = session.root / _INDEX_NAME
    save_json(path, index)
    return index


def query_session_corpus(session_id: str, question: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Keyword-ranked retrieval over indexed session chunks."""
    session = load_session(session_id)
    index_path = session.root / _INDEX_NAME
    if not index_path.exists():
        build_session_corpus(session_id)
    data = load_json(index_path, default={"chunks": []})
    chunks = list(data.get("chunks") or [])
    if not chunks:
        return []

    q_tokens = _tokenize(question)
    if not q_tokens:
        return chunks[:top_k]

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "")
        tokens = _tokenize(text)
        overlap = len(q_tokens & tokens)
        if overlap:
            scored.append((overlap / len(q_tokens), chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def format_corpus_context(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return ""
    lines = ["## Retrieved session corpus excerpts"]
    for hit in hits:
        lines.append(f"\n**Source:** `{hit.get('source')}`")
        lines.append(str(hit.get("text") or "")[:1500])
    return "\n".join(lines)
