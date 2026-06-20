"""Summarize downloaded PDF papers in the active session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cursor_sdk import CustomTool, CustomToolContext

from deep_research.session_context import get_active_session, list_session_files
from deep_research.tools.paths import PROJECT_ROOT, ensure_dir, relative_to_project_path, slugify


def _extract_pdf_text(path: Path, *, max_chars: int = 12000) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise ValueError("pymupdf is required for paper summaries. pip install pymupdf") from exc

    doc = fitz.open(path)
    chunks: list[str] = []
    total = 0
    for page in doc:
        text = page.get_text().strip()
        if not text:
            continue
        chunks.append(text)
        total += len(text)
        if total >= max_chars:
            break
    doc.close()
    combined = "\n\n".join(chunks)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n\n[... truncated ...]"
    return combined


def _build_summary_markdown(title: str, text: str) -> str:
    """Structured summary scaffold for the agent or host to fill via synthesis."""
    preview = text[:2000].strip()
    return (
        f"# Paper summary: {title}\n\n"
        f"## Key claims (extract from text)\n"
        f"- [Agent: populate from content below]\n\n"
        f"## Methods / evidence quality\n"
        f"- [Agent: note study design if present]\n\n"
        f"## Limitations\n"
        f"- [Agent: note sample size, conflicts, gaps]\n\n"
        f"## Source excerpt\n\n"
        f"{preview}\n"
    )


def summarize_downloaded_papers(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """Extract text from session PDFs and write structured summaries to Papers/summaries/."""
    session = get_active_session()
    if session is None:
        raise ValueError("No active research session")

    papers = list_session_files(session, "Papers")
    pdf_files = [p for p in papers if p.suffix.lower() == ".pdf"]
    if not pdf_files:
        raise ValueError("No PDF files in session Papers/ folder")

    summaries_dir = ensure_dir(session.root / "Papers" / "summaries")
    outcomes: list[dict[str, Any]] = []

    for pdf_path in pdf_files:
        entry: dict[str, Any] = {"source_pdf": str(pdf_path.relative_to(PROJECT_ROOT))}
        try:
            text = _extract_pdf_text(pdf_path)
            title = pdf_path.stem.replace("-", " ").replace("_", " ")
            summary_body = str(args.get("summary_body") or "").strip()
            if summary_body:
                content = f"# Paper summary: {title}\n\n{summary_body}\n\n## Source\n`{entry['source_pdf']}`\n"
            else:
                content = _build_summary_markdown(title, text)
            out_name = slugify(pdf_path.stem) + "_summary.md"
            out_path = summaries_dir / out_name
            out_path.write_text(content, encoding="utf-8")
            entry["status"] = "written"
            entry["summary_path"] = relative_to_project_path(out_path)
            entry["chars_extracted"] = len(text)
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
        outcomes.append(entry)

    written = sum(1 for o in outcomes if o.get("status") == "written")
    return json.dumps(
        {
            "summaries_directory": str(summaries_dir.relative_to(PROJECT_ROOT)),
            "processed": len(pdf_files),
            "written": written,
            "summaries": outcomes,
        },
        indent=2,
    )


SUMMARIZE_PAPERS_TOOL = CustomTool(
    execute=summarize_downloaded_papers,
    description=(
        "Summarize PDFs already downloaded in the session Papers/ folder. "
        "Writes structured markdown summaries to Papers/summaries/. "
        "Optionally pass summary_body with your synthesized summary per paper batch."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "summary_body": {
                "type": "string",
                "description": "Optional agent-written summary text to save (otherwise scaffold + excerpt).",
            },
        },
    },
)
