"""Export helpers — report PDF, enhanced session ZIP."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from deep_research.session_context import ResearchSession, list_session_files, load_session


def markdown_to_pdf_bytes(markdown_text: str, *, title: str = "Research Report") -> bytes:
    """Create a simple PDF from markdown/plain text using PyMuPDF."""
    try:
        import fitz
    except ImportError as exc:
        raise ValueError("pymupdf required: pip install pymupdf") from exc

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(50, 50, 545, 792)
    header = f"{title}\n\n"
    page.insert_textbox(rect, header + markdown_text[:50000], fontsize=10, fontname="helv")
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    buffer.seek(0)
    return buffer.getvalue()


def report_pdf_for_session(session: ResearchSession) -> bytes | None:
    """Return PDF bytes from first .md report or session answer."""
    reports = list_session_files(session, "Reports")
    text = ""
    for path in reports:
        if path.suffix.lower() == ".md":
            text = path.read_text(encoding="utf-8")
            title = path.stem
            return markdown_to_pdf_bytes(text, title=title)
    if session.answer:
        return markdown_to_pdf_bytes(session.answer, title=session.display_title())
    return None


def export_session_zip_enhanced(session_id: str) -> bytes:
    """ZIP all artifacts plus answer.md and sources.json."""
    from deep_research.session_context import export_session_zip

    session = load_session(session_id)
    base_zip = export_session_zip(session_id)
    buffer = io.BytesIO(base_zip)
    with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED) as archive:
        if session.answer:
            archive.writestr("answer.md", session.answer)
        sources = session.root / "sources.json"
        if sources.exists():
            archive.write(sources, arcname="sources.json")
        corpus = session.root / "corpus_index.json"
        if corpus.exists():
            archive.write(corpus, arcname="corpus_index.json")
    buffer.seek(0)
    return buffer.getvalue()
