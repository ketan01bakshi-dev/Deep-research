"""Enhanced PDF download with landing-page PDF discovery fallback."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from cursor_sdk import CustomTool, CustomToolContext

from cursor_agent_core.outputs.pdf_download import download_research_pdfs as _download_direct

_PDF_HREF_RE = re.compile(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', re.IGNORECASE)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def _discover_pdf_urls(landing_url: str, *, limit: int = 3) -> list[str]:
    """Fetch HTML page and extract direct .pdf hrefs."""
    request = Request(landing_url, headers={"User-Agent": "DeepResearchAgent/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    parser = _LinkParser()
    parser.feed(html)
    discovered: list[str] = []
    for href in parser.links:
        absolute = urljoin(landing_url, href)
        if absolute.lower().endswith(".pdf") or ".pdf?" in absolute.lower():
            if absolute not in discovered:
                discovered.append(absolute)
        if len(discovered) >= limit:
            break
    return discovered


def _expand_urls(urls: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        if url.lower().endswith(".pdf") or ".pdf?" in url.lower():
            expanded.append(url)
            continue
        for pdf_url in _discover_pdf_urls(url):
            if pdf_url not in seen:
                seen.add(pdf_url)
                expanded.append(pdf_url)
    return expanded


def download_research_pdfs_enhanced(
    args: dict[str, Any],
    ctx: CustomToolContext,
) -> str:
    """Download PDFs; discover PDF links from landing pages when direct URL fails."""
    raw_urls = args.get("pdf_urls") or []
    if isinstance(raw_urls, str):
        urls = [raw_urls]
    else:
        urls = [str(u).strip() for u in raw_urls if str(u).strip()]
    if not urls:
        raise ValueError("pdf_urls is required")

    expanded = _expand_urls(urls)
    if not expanded:
        return json.dumps(
            {
                "requested": len(urls),
                "downloaded": 0,
                "failed": len(urls),
                "message": "No direct or discoverable PDF URLs found.",
                "landing_urls_tried": urls,
            },
            indent=2,
        )

    payload_str = _download_direct({"pdf_urls": expanded}, ctx)
    payload = json.loads(payload_str)
    payload["landing_urls_expanded"] = urls
    payload["resolved_pdf_urls"] = expanded
    return json.dumps(payload, indent=2)


DOWNLOAD_PDFS_ENHANCED_TOOL = CustomTool(
    execute=download_research_pdfs_enhanced,
    description=(
        "Download research PDFs from direct URLs or article landing pages. "
        "When a URL is not a .pdf, attempts to find PDF links on the page."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "pdf_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Direct PDF URLs or article landing pages.",
            },
        },
        "required": ["pdf_urls"],
    },
)
