"""Tests for PDF enhanced download URL expansion."""

from __future__ import annotations

from deep_research.tools.pdf_enhanced import _expand_urls


def test_expand_urls_keeps_direct_pdf():
    urls = ["https://example.com/paper.pdf"]
    assert _expand_urls(urls) == urls


def test_expand_urls_dedupes():
    urls = [
        "https://example.com/a.pdf",
        "https://example.com/a.pdf",
    ]
    assert len(_expand_urls(urls)) == 1
