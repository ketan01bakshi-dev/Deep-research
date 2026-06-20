"""Download research PDFs from URLs returned by literature search."""

from __future__ import annotations

import json
import ssl
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import certifi

from cursor_sdk import CustomTool, CustomToolContext

from cursor_agent_core.paths.file_helpers import (
    relative_to_project,
    sanitize_filename,
    slugify,
    unique_path,
    utc_timestamp,
)
from cursor_agent_core.paths.project_context import get_output_directory, get_project_root

_USER_AGENT = "DeepResearchAgent/1.0 (research PDF downloader)"


def _safe_filename(url: str, index: int) -> str:
    path_name = unquote(Path(urlparse(url).path).name)
    if path_name.lower().endswith(".pdf") and len(path_name) > 4:
        stem = path_name[:-4]
    else:
        stem = path_name or f"paper_{index}"

    stem = sanitize_filename(stem, fallback=f"paper_{index}")
    return f"{stem[:180]}.pdf"


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _download_pdf(url: str, dest: Path) -> None:
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=60, context=_ssl_context()) as response:
        content_type = (response.headers.get("Content-Type") or "").lower()
        data = response.read()
        if "pdf" not in content_type and not data.startswith(b"%PDF"):
            raise ValueError(
                f"URL did not return a PDF (content-type: {content_type or 'unknown'})"
            )
        dest.write_bytes(data)


def download_research_pdfs(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """Download PDFs from a list of URLs into the active session Papers/ folder."""
    raw_urls = args.get("pdf_urls")
    if not raw_urls:
        raise ValueError("pdf_urls is required (non-empty list of PDF URLs)")

    if isinstance(raw_urls, str):
        urls = [raw_urls]
    elif isinstance(raw_urls, list):
        urls = [str(u).strip() for u in raw_urls if str(u).strip()]
    else:
        raise ValueError("pdf_urls must be a list of URL strings")

    if not urls:
        raise ValueError("pdf_urls must contain at least one URL")

    directory = get_output_directory('papers')
    outcomes: list[dict[str, Any]] = []

    for index, url in enumerate(urls, start=1):
        entry: dict[str, Any] = {"url": url}
        try:
            dest = unique_path(directory, _safe_filename(url, index))
            _download_pdf(url, dest)
            entry["status"] = "downloaded"
            entry["path"] = str(dest.relative_to(get_project_root()))
            entry["size_bytes"] = dest.stat().st_size
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
        outcomes.append(entry)

    downloaded = sum(1 for item in outcomes if item["status"] == "downloaded")
    payload = {
        "papers_directory": str(directory.relative_to(get_project_root())),
        "requested": len(urls),
        "downloaded": downloaded,
        "failed": len(urls) - downloaded,
        "files": outcomes,
    }
    return json.dumps(payload, indent=2)


DOWNLOAD_PDFS_TOOL = CustomTool(
    execute=download_research_pdfs,
    description=(
        "Download research PDFs from URLs (typically from search_research_literature "
        "pdf_urls or direct .pdf links) and save them to the session Papers/ folder."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "pdf_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of direct PDF URLs to download.",
            },
        },
        "required": ["pdf_urls"],
    },
)
